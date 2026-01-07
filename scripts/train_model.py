#!/usr/bin/env python3
"""
XGBoost Model Training Script for Trading Bot.

This script:
1. Fetches 6 months of historical OHLCV data for all symbols
2. Engineers features using existing TechnicalFeatures
3. Labels data (1 = price +2% in next 4 hours)
4. Trains XGBoost classifier with hyperparameter optimization
5. Saves model and feature columns for SignalGenerator integration

Usage:
    python scripts/train_model.py                  # Full training
    python scripts/train_model.py --test           # Quick test mode (1 month, no tuning)
    python scripts/train_model.py --symbols BTC/EUR,ETH/EUR  # Specific symbols
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import asyncio
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd
import ccxt
from loguru import logger
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    classification_report, roc_auc_score, accuracy_score, 
    precision_score, recall_score, f1_score
)

try:
    import xgboost as xgb
    from xgboost import XGBClassifier
except ImportError:
    logger.error("XGBoost not installed. Run: pip install xgboost")
    sys.exit(1)

try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    logger.warning("Optuna not installed - hyperparameter tuning disabled")
    OPTUNA_AVAILABLE = False

from src.config.settings import settings
from src.features.technical import TechnicalFeatures

# ============================================================================
# CONFIGURATION
# ============================================================================

# Label configuration
LOOKAHEAD_PERIODS = 16  # 16 x 15min = 4 hours
PRICE_THRESHOLD = 0.02  # 2% price increase for positive label

# Feature columns to use (must match what model expects at inference)
FEATURE_COLUMNS = [
    # Momentum
    'RSI_14', 'RSI_7', 'STOCHk_14_3_3', 'STOCHd_14_3_3', 'ROC_10',
    # Trend
    'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9',
    'ADX_14', 'DMP_14', 'DMN_14',
    # Volatility
    'bb_position', 'bb_width', 'ATRr_14',
    # Volume
    'volume_ratio', 'OBV',
    # Custom
    'price_vs_sma20', 'price_vs_sma50',
    'return_1h', 'return_4h', 'return_24h',
    'volatility_20', 'higher_high', 'lower_low',
    'is_bullish_candle', 'trend_strong', 'rsi_divergence'
]

# Model paths
MODELS_DIR = Path(__file__).parent.parent / "src" / "ml" / "models"
MODEL_PATH = MODELS_DIR / "xgb_model.pkl"
FEATURES_PATH = MODELS_DIR / "feature_columns.json"
TRAINING_REPORT_PATH = Path(__file__).parent.parent / "logs" / "training_report.json"

# ============================================================================
# DATA FETCHING
# ============================================================================

async def fetch_historical_data(
    symbols: List[str],
    months: int = 6,
    timeframe: str = '15m'
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical OHLCV data for all symbols.
    
    Args:
        symbols: List of trading pairs
        months: Number of months of history
        timeframe: Candle timeframe
        
    Returns:
        Dictionary mapping symbol -> DataFrame
    """
    logger.info(f"📊 Fetching {months} months of {timeframe} data for {len(symbols)} symbols...")
    
    exchange = ccxt.kraken({'enableRateLimit': True})
    
    # Calculate time range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    since = int(start_date.timestamp() * 1000)
    
    data = {}
    
    for symbol in symbols:
        try:
            logger.info(f"  Fetching {symbol}...")
            all_candles = []
            current_since = since
            
            while True:
                candles = await asyncio.to_thread(
                    exchange.fetch_ohlcv,
                    symbol, timeframe, current_since, 1000
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                current_since = candles[-1][0] + 1
                
                # Stop if we've reached current time
                if candles[-1][0] > int(datetime.now().timestamp() * 1000):
                    break
                    
                # Rate limiting
                await asyncio.sleep(0.5)
            
            if all_candles:
                df = pd.DataFrame(
                    all_candles,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['symbol'] = symbol
                data[symbol] = df
                logger.info(f"    ✓ {symbol}: {len(df)} candles")
            
        except Exception as e:
            logger.error(f"    ✗ {symbol}: {e}")
            continue
    
    return data


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply technical analysis features to OHLCV data.
    
    Args:
        df: Raw OHLCV DataFrame
        
    Returns:
        DataFrame with technical features added
    """
    # Use existing TechnicalFeatures class
    df = TechnicalFeatures.add_all_features(df, include_advanced=True)
    
    # Ensure all required columns exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            logger.warning(f"Feature {col} not found, filling with 0")
            df[col] = 0
    
    return df


def create_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create target labels based on future price movement.
    
    Label = 1 if price increases by >= PRICE_THRESHOLD within LOOKAHEAD_PERIODS
    Label = 0 otherwise
    
    Args:
        df: DataFrame with close prices
        
    Returns:
        DataFrame with 'target' column added
    """
    # Calculate max price in next N periods
    df['future_max'] = df['close'].shift(-1).rolling(LOOKAHEAD_PERIODS).max().shift(-LOOKAHEAD_PERIODS + 1)
    
    # Calculate return from current close to future max
    df['future_return'] = (df['future_max'] - df['close']) / df['close']
    
    # Create binary label
    df['target'] = (df['future_return'] >= PRICE_THRESHOLD).astype(int)
    
    # Drop rows where we can't calculate future return (end of dataset)
    df = df.dropna(subset=['target'])
    
    # Clean up temporary columns
    df = df.drop(columns=['future_max', 'future_return'])
    
    return df


# ============================================================================
# MODEL TRAINING
# ============================================================================

def prepare_training_data(
    data: Dict[str, pd.DataFrame]
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare combined training dataset from all symbols.
    
    Args:
        data: Dictionary of symbol -> DataFrame
        
    Returns:
        Tuple of (features DataFrame, targets Series)
    """
    all_dfs = []
    
    for symbol, df in data.items():
        logger.info(f"  Processing {symbol}...")
        
        # Engineer features
        df = engineer_features(df)
        
        # Create labels
        df = create_labels(df)
        
        if len(df) > 100:  # Minimum samples
            all_dfs.append(df)
    
    # Combine all data
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    
    # Drop rows with NaN in features
    available_features = [f for f in FEATURE_COLUMNS if f in combined.columns]
    combined = combined.dropna(subset=available_features + ['target'])
    
    logger.info(f"📋 Combined dataset: {len(combined)} samples")
    logger.info(f"   Positive class (BUY signals): {combined['target'].sum()} ({combined['target'].mean()*100:.1f}%)")
    logger.info(f"   Negative class (HOLD/SELL): {len(combined) - combined['target'].sum()}")
    
    X = combined[available_features]
    y = combined['target']
    
    return X, y


def train_with_optuna(
    X: pd.DataFrame, 
    y: pd.Series,
    n_trials: int = 30
) -> XGBClassifier:
    """
    Train XGBoost with Optuna hyperparameter optimization.
    
    Args:
        X: Features DataFrame
        y: Target Series
        n_trials: Number of Optuna trials
        
    Returns:
        Trained XGBClassifier
    """
    def objective(trial):
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'subsample': trial.suggest_float('subsample', 0.6, 0.95),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 1.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 1.0, log=True),
            'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1, 5),
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': 0
        }
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model = XGBClassifier(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            
            y_pred_proba = model.predict_proba(X_val)[:, 1]
            score = roc_auc_score(y_val, y_pred_proba)
            scores.append(score)
        
        return np.mean(scores)
    
    # Run optimization
    logger.info(f"🔬 Starting Optuna optimization with {n_trials} trials...")
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction='maximize',
        sampler=TPESampler(seed=42)
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    logger.info(f"   Best AUC: {study.best_value:.4f}")
    logger.info(f"   Best params: {study.best_params}")
    
    # Train final model with best params
    best_params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'random_state': 42,
        'n_jobs': -1,
        **study.best_params
    }
    
    # Final train/test split (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    model = XGBClassifier(**best_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    return model


def train_default(X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
    """
    Train XGBoost with default parameters (fast, no optimization).
    
    Args:
        X: Features DataFrame
        y: Target Series
        
    Returns:
        Trained XGBClassifier
    """
    logger.info("🚀 Training with default parameters (no Optuna)...")
    
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 200,
        'min_child_weight': 3,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'scale_pos_weight': 2,
        'random_state': 42,
        'n_jobs': -1
    }
    
    # Train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    model = XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=True
    )
    
    return model


def evaluate_model(
    model: XGBClassifier,
    X: pd.DataFrame,
    y: pd.Series
) -> Dict:
    """
    Evaluate model performance on test set.
    
    Args:
        model: Trained XGBClassifier
        X: Features DataFrame
        y: Targets Series
        
    Returns:
        Dictionary of metrics
    """
    # Use last 20% as test set
    split_idx = int(len(X) * 0.8)
    X_test = X.iloc[split_idx:]
    y_test = y.iloc[split_idx:]
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
        'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
        'test_samples': len(y_test),
        'positive_rate': float(y_test.mean()),
        'predicted_positive_rate': float(y_pred.mean())
    }
    
    return metrics


def save_model(
    model: XGBClassifier,
    feature_columns: List[str],
    metrics: Dict
) -> None:
    """
    Save trained model, feature columns, and training report.
    
    Args:
        model: Trained XGBClassifier
        feature_columns: List of feature column names
        metrics: Training metrics dictionary
    """
    # Ensure directories exist
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Save model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"✅ Model saved to {MODEL_PATH}")
    
    # Save feature columns
    with open(FEATURES_PATH, 'w') as f:
        json.dump(feature_columns, f, indent=2)
    logger.info(f"✅ Feature columns saved to {FEATURES_PATH}")
    
    # Save training report
    report = {
        'timestamp': datetime.now().isoformat(),
        'feature_columns': feature_columns,
        'metrics': metrics,
        'model_params': model.get_params()
    }
    with open(TRAINING_REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)
    logger.info(f"✅ Training report saved to {TRAINING_REPORT_PATH}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description='Train XGBoost model for trading signals')
    parser.add_argument('--test', action='store_true', help='Quick test mode (1 month, no tuning)')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (default: all)')
    parser.add_argument('--months', type=int, default=6, help='Months of historical data')
    parser.add_argument('--trials', type=int, default=30, help='Optuna trials for hyperparameter search')
    args = parser.parse_args()
    
    # Configuration
    if args.test:
        months = 1
        use_optuna = False
        symbols = ['BTC/EUR', 'ETH/EUR']
        logger.info("🧪 TEST MODE: 1 month, 2 symbols, no tuning")
    else:
        months = args.months
        use_optuna = OPTUNA_AVAILABLE
        symbols = args.symbols.split(',') if args.symbols else settings.SYMBOLS
    
    logger.info("=" * 60)
    logger.info("🤖 XGBoost Training Pipeline")
    logger.info("=" * 60)
    logger.info(f"   Symbols: {symbols}")
    logger.info(f"   Months: {months}")
    logger.info(f"   Optuna: {use_optuna}")
    logger.info("=" * 60)
    
    # Step 1: Fetch data
    data = await fetch_historical_data(symbols, months)
    
    if not data:
        logger.error("❌ No data fetched. Exiting.")
        return
    
    # Step 2: Prepare training data
    logger.info("🔧 Preparing training data...")
    X, y = prepare_training_data(data)
    
    if len(X) < 1000:
        logger.error(f"❌ Insufficient data ({len(X)} samples). Need at least 1000.")
        return
    
    # Get actual available features
    available_features = list(X.columns)
    logger.info(f"   Using {len(available_features)} features")
    
    # Step 3: Train model
    logger.info("🎯 Training XGBoost model...")
    if use_optuna:
        model = train_with_optuna(X, y, n_trials=args.trials)
    else:
        model = train_default(X, y)
    
    # Step 4: Evaluate
    logger.info("📊 Evaluating model...")
    metrics = evaluate_model(model, X, y)
    
    logger.info("=" * 60)
    logger.info("📈 MODEL PERFORMANCE")
    logger.info("=" * 60)
    logger.info(f"   Accuracy:  {metrics['accuracy']:.2%}")
    logger.info(f"   Precision: {metrics['precision']:.2%}")
    logger.info(f"   Recall:    {metrics['recall']:.2%}")
    logger.info(f"   F1 Score:  {metrics['f1_score']:.2%}")
    logger.info(f"   ROC AUC:   {metrics['roc_auc']:.4f}")
    logger.info("=" * 60)
    
    # Check if model meets minimum requirements
    if metrics['roc_auc'] < 0.55:
        logger.warning("⚠️ Model AUC below 0.55 - may not be reliable!")
    else:
        logger.info("✅ Model meets minimum AUC threshold (0.55)")
    
    # Step 5: Save
    logger.info("💾 Saving model...")
    save_model(model, available_features, metrics)
    
    logger.info("=" * 60)
    logger.info("🎉 TRAINING COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"   Model ready at: {MODEL_PATH}")
    logger.info("   The SignalGenerator will automatically load this model.")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
