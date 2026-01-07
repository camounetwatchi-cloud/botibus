"""
ML Signal Generator - Ensemble of Technical and ML-based signals.

Combines multiple signal sources to generate high-confidence trading signals.
"""
import json
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger
from pathlib import Path
import pickle
from src.config.settings import settings


@dataclass  
class MLSignal:
    """Container for ML-generated signal."""
    action: str  # BUY, SELL, HOLD
    confidence: float
    technical_score: float
    ml_score: float
    volume_score: float
    reasons: List[str]
    atr: float = 0.0  # ATR for dynamic TP calculation
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal is strong enough to act on."""
        return self.action != "HOLD" and self.confidence >= 0.10  # Ultra-aggressive


class SignalGenerator:
    """
    Ensemble signal generator combining:
    - Technical indicator analysis (40%)
    - ML model predictions (40%)
    - Volume/Momentum confirmation (20%)
    """
    
    WEIGHTS = {
        'technical': 0.40,
        'ml': 0.40,
        'volume_momentum': 0.20,
    }
    
    # Thresholds - Use settings as single source of truth
    MIN_CONFIDENCE = settings.MIN_SIGNAL_CONFIDENCE  # From settings (0.20)
    STRONG_SIGNAL_THRESHOLD = settings.STRONG_SIGNAL_THRESHOLD  # From settings (0.70)
    ACTION_THRESHOLD = 0.15  # Minimum score to trigger action (avoid ultra-weak signals)
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize signal generator.
        
        Args:
            model_path: Path to trained XGBoost model (optional)
        """
        self.model = None
        self.model_loaded = False
        self.feature_columns = None
        
        # Default model paths
        models_dir = Path(__file__).parent / "models"
        default_model_path = models_dir / "xgb_model.pkl"
        default_features_path = models_dir / "feature_columns.json"
        
        # Determine which model path to use
        path_to_load = Path(model_path) if model_path else default_model_path
        features_to_load = default_features_path
        
        if path_to_load.exists():
            try:
                with open(path_to_load, 'rb') as f:
                    self.model = pickle.load(f)
                
                # Load feature columns
                if features_to_load.exists():
                    with open(features_to_load, 'r') as f:
                        self.feature_columns = json.load(f)
                    logger.info(f"✅ XGBoost model loaded from {path_to_load}")
                    logger.info(f"   Using {len(self.feature_columns)} features")
                    self.model_loaded = True
                else:
                    logger.warning(f"❌ Model found but feature columns missing at {features_to_load}")
                    self.model = None
                    self.model_loaded = False
                    
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")
                self.model = None
                self.model_loaded = False
        else:
            logger.info("ℹ️ No trained XGBoost model found, using heuristics")
    
    def generate(self, df: pd.DataFrame, symbol: str = "") -> MLSignal:
        """
        Generate trading signal from OHLCV data with indicators.
        
        Args:
            df: DataFrame with OHLCV and technical indicators
            symbol: Symbol being analyzed (for logging)
            
        Returns:
            MLSignal with action and confidence
        """
        if df.empty or len(df) < 20:
            return MLSignal(
                action="HOLD",
                confidence=0,
                technical_score=0,
                ml_score=0,
                volume_score=0,
                reasons=["Insufficient data"]
            )
        
        reasons = []
        
        # === 1. Technical Analysis Score ===
        tech_score, tech_reasons = self._calculate_technical_score(df)
        reasons.extend(tech_reasons)
        
        # === 2. ML Model Score ===
        ml_score, ml_reason = self._calculate_ml_score(df)
        if ml_reason:
            reasons.append(ml_reason)
        
        # === 3. Volume/Momentum Score ===
        vol_score, vol_reason = self._calculate_volume_momentum_score(df)
        if vol_reason:
            reasons.append(vol_reason)
        
        # === Calculate Weighted Ensemble Score ===
        total_score = (
            tech_score * self.WEIGHTS['technical'] +
            ml_score * self.WEIGHTS['ml'] +
            vol_score * self.WEIGHTS['volume_momentum']
        )
        
        # Normalize to [-1, 1]
        normalized_score = np.clip(total_score, -1, 1)
        
        # Determine action and confidence
        confidence = abs(normalized_score)
        
        # AGGRESSIVE: Only check threshold, confidence is informational
        if normalized_score >= self.ACTION_THRESHOLD:
            action = "BUY"
        elif normalized_score <= -self.ACTION_THRESHOLD:
            action = "SELL"
        else:
            action = "HOLD"
        
        signal = MLSignal(
            action=action,
            confidence=confidence,
            technical_score=tech_score,
            ml_score=ml_score,
            volume_score=vol_score,
            reasons=reasons[:5]  # Limit to top 5 reasons
        )
        
        if signal.is_actionable:
            logger.info(
                f"[{symbol}] Signal: {action} (conf: {confidence:.2f}) | "
                f"Tech: {tech_score:.2f}, ML: {ml_score:.2f}, Vol: {vol_score:.2f}"
            )
        
        return signal
    
    def _calculate_technical_score(self, df: pd.DataFrame) -> Tuple[float, List[str]]:
        """Calculate score from technical indicators."""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        score = 0
        reasons = []
        
        # --- RSI Analysis ---
        rsi = latest.get('RSI_14', 50)
        if not pd.isna(rsi):
            if rsi <= 25:
                score += 0.9
                reasons.append(f"RSI deeply oversold ({rsi:.0f})")
            elif rsi <= 40:  # Widened from 35
                score += 0.5
                reasons.append(f"RSI oversold ({rsi:.0f})")
            elif rsi >= 75:
                score -= 0.9
                reasons.append(f"RSI deeply overbought ({rsi:.0f})")
            elif rsi >= 60:  # Widened from 65
                score -= 0.5
                reasons.append(f"RSI overbought ({rsi:.0f})")
        
        # --- MACD Analysis ---
        macd_hist = latest.get('MACDh_12_26_9', 0)
        prev_macd_hist = prev.get('MACDh_12_26_9', 0)
        
        if not pd.isna(macd_hist) and not pd.isna(prev_macd_hist):
            # Bullish crossover
            if prev_macd_hist < 0 and macd_hist > 0:
                score += 0.7
                reasons.append("MACD bullish crossover")
            # Bearish crossover
            elif prev_macd_hist > 0 and macd_hist < 0:
                score -= 0.7
                reasons.append("MACD bearish crossover")
            # Growing bullish momentum
            elif macd_hist > 0 and macd_hist > prev_macd_hist:
                score += 0.3
            # Growing bearish momentum
            elif macd_hist < 0 and macd_hist < prev_macd_hist:
                score -= 0.3
        
        # --- Bollinger Bands ---
        close = latest.get('close', 0)
        bb_lower = latest.get('BBL_20_2.0', 0)
        bb_upper = latest.get('BBU_20_2.0', 0)
        
        if bb_lower > 0 and bb_upper > bb_lower:
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            
            if bb_position <= 0.05:
                score += 0.6
                reasons.append("Price at lower BB (bounce potential)")
            elif bb_position <= 0.2:
                score += 0.3
            elif bb_position >= 0.95:
                score -= 0.6
                reasons.append("Price at upper BB (reversal risk)")
            elif bb_position >= 0.8:
                score -= 0.3
        
        # --- Trend Analysis (SMAs) ---
        sma20 = latest.get('SMA_20', 0)
        sma50 = latest.get('SMA_50', 0)
        
        if sma20 > 0 and sma50 > 0:
            if close > sma20 > sma50:
                score += 0.4
                reasons.append("Bullish trend (price > SMA20 > SMA50)")
            elif close < sma20 < sma50:
                score -= 0.4
                reasons.append("Bearish trend (price < SMA20 < SMA50)")
        
        # --- Stochastic ---
        stoch_k = latest.get('STOCHk_14_3_3', 50)
        stoch_d = latest.get('STOCHd_14_3_3', 50)
        
        if not pd.isna(stoch_k):
            if stoch_k <= 20:
                score += 0.3
            elif stoch_k >= 80:
                score -= 0.3
        
        # Normalize score to [-1, 1]
        return np.clip(score / 2.5, -1, 1), reasons
    
    def _calculate_ml_score(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate score from ML model prediction (binary classification)."""
        if not self.model_loaded or self.model is None:
            # Fallback: use simplified heuristic when no model
            return self._heuristic_ml_score(df)
        
        try:
            # Prepare features for model
            features_df = self._prepare_features(df)
            
            if features_df is None:
                return self._heuristic_ml_score(df)
            
            # Get prediction probability for positive class (BUY)
            # Model is binary: 0 = no signal, 1 = BUY opportunity
            proba = self.model.predict_proba(features_df)[0]
            buy_prob = proba[1]  # Probability of class 1 (BUY)
            
            # Convert probability [0, 1] to score [-1, 1]
            # prob > 0.5 means BUY, prob < 0.5 means SELL/HOLD
            score = (buy_prob - 0.5) * 2
            
            reason = ""
            if buy_prob >= 0.65:
                reason = f"ML: Strong BUY signal ({buy_prob:.0%})"
            elif buy_prob >= 0.55:
                reason = f"ML: Moderate BUY signal ({buy_prob:.0%})"
            elif buy_prob <= 0.35:
                reason = f"ML: SELL signal ({buy_prob:.0%})"
            elif buy_prob <= 0.45:
                reason = f"ML: Weak SELL signal ({buy_prob:.0%})"
            
            return score, reason
            
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}")
            return self._heuristic_ml_score(df)
    
    def _heuristic_ml_score(self, df: pd.DataFrame) -> Tuple[float, str]:
        """
        Heuristic ML-like score based on pattern recognition.
        AGGRESSIVE MODE: Lower thresholds for more signals.
        """
        if len(df) < 10:
            return 0, ""
        
        # Calculate recent returns
        returns = df['close'].pct_change().tail(10)
        
        # Check for trend
        avg_return = returns.mean()
        return_std = returns.std()
        
        # AGGRESSIVE: Much lower thresholds for trend detection
        if avg_return > 0.002:  # Lowered from 0.005
            score = 0.6  # Increased from 0.5
            reason = "Bullish momentum pattern"
        elif avg_return < -0.002:  # Lowered from -0.005
            score = -0.6  # Increased from -0.5
            reason = "Bearish momentum pattern"
        elif avg_return < -0.001 and return_std < 0.015:
            # Micro-dip with low volatility - potential bounce
            score = 0.4
            reason = "Potential reversal pattern"
        elif avg_return > 0.001 and return_std < 0.015:
            # Micro-rally with low volatility - potential drop
            score = -0.4
            reason = "Potential reversal pattern"
        else:
            # AGGRESSIVE: Even neutral market gets a small bias
            # based on last 3 candles direction
            recent_3 = df['close'].tail(3).pct_change().dropna()
            if len(recent_3) >= 2:
                if all(r > 0 for r in recent_3):
                    score = 0.3
                    reason = "Short-term bullish"
                elif all(r < 0 for r in recent_3):
                    score = -0.3
                    reason = "Short-term bearish"
                else:
                    score = 0
                    reason = ""
            else:
                score = 0
                reason = ""
        
        return score, reason
    
    def _calculate_volume_momentum_score(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate score from volume and momentum."""
        if len(df) < 20:
            return 0, ""
        
        score = 0
        reason = ""
        
        latest = df.iloc[-1]
        
        # --- Volume Analysis ---
        if 'volume' in df.columns:
            avg_vol = df['volume'].tail(20).mean()
            latest_vol = latest['volume']
            
            if avg_vol > 0:
                vol_ratio = latest_vol / avg_vol
                
                if vol_ratio >= 2.0:
                    score += 0.4
                    reason = f"High volume confirmation ({vol_ratio:.1f}x)"
                elif vol_ratio >= 1.5:
                    score += 0.2
                elif vol_ratio < 0.5:
                    score -= 0.2  # Low volume = weak signal
        
        # --- Momentum ---
        close_5 = df.iloc[-5]['close'] if len(df) >= 5 else df.iloc[0]['close']
        momentum = (latest['close'] - close_5) / close_5 * 100
        
        if momentum >= 2.0:
            score += 0.4
            reason = f"Strong momentum (+{momentum:.1f}%)"
        elif momentum >= 1.0:
            score += 0.2
        elif momentum <= -2.0:
            score -= 0.4
            reason = f"Weak momentum ({momentum:.1f}%)"
        elif momentum <= -1.0:
            score -= 0.2
        
        # --- OBV Trend ---
        obv = latest.get('OBV', None)
        if obv is not None and len(df) >= 5:
            obv_prev = df.iloc[-5].get('OBV', obv)
            if obv > obv_prev * 1.02:
                score += 0.2
            elif obv < obv_prev * 0.98:
                score -= 0.2
        
        return np.clip(score, -1, 1), reason
    
    def _prepare_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Prepare feature DataFrame for ML model.
        
        Uses the same feature columns that were used during training.
        """
        if self.feature_columns is None:
            logger.warning("No feature columns loaded, cannot prepare features")
            return None
        
        latest = df.iloc[[-1]]  # Get last row as DataFrame
        
        # Select only the columns used during training
        available_cols = [c for c in self.feature_columns if c in latest.columns]
        
        if len(available_cols) < len(self.feature_columns) * 0.5:
            logger.warning(f"Missing too many features: {len(available_cols)}/{len(self.feature_columns)}")
            return None
        
        # Create feature DataFrame with expected columns
        features = pd.DataFrame(columns=self.feature_columns)
        
        for col in self.feature_columns:
            if col in latest.columns:
                features[col] = latest[col].values
            else:
                # Fill missing with 0
                features[col] = 0
        
        # Replace NaN with 0
        features = features.fillna(0)
        
        return features


def create_signal_generator(model_path: Optional[str] = None) -> SignalGenerator:
    """Factory function to create signal generator."""
    return SignalGenerator(model_path=model_path)
