"""
Technical Features - Enhanced indicator calculation.

Provides comprehensive technical analysis features for trading signals.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from loguru import logger
from typing import Optional


class TechnicalFeatures:
    """Technical indicator calculator using pandas-ta."""
    
    @staticmethod
    def add_all_features(df: pd.DataFrame, include_advanced: bool = True) -> pd.DataFrame:
        """
        Add all technical indicators to OHLCV DataFrame.
        
        Args:
            df: DataFrame with OHLCV columns
            include_advanced: Include advanced indicators (slower)
            
        Returns:
            DataFrame with added indicator columns
        """
        if df.empty or len(df) < 5:
            logger.warning("Insufficient data for technical analysis")
            return df
            
        df = df.copy()
        
        # Ensure column names are correct
        df.columns = df.columns.str.lower()
        
        try:
            # === TREND INDICATORS ===
            # Simple Moving Averages
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            if len(df) >= 200:
                df.ta.sma(length=200, append=True)
            
            # Exponential Moving Averages
            df.ta.ema(length=12, append=True)
            df.ta.ema(length=26, append=True)
            df.ta.ema(length=50, append=True)
            
            # MACD
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            
            # ADX - Trend Strength
            if include_advanced:
                df.ta.adx(length=14, append=True)
            
            # === MOMENTUM INDICATORS ===
            # RSI
            df.ta.rsi(length=14, append=True)
            df.ta.rsi(length=7, append=True)
            
            # Stochastic
            df.ta.stoch(k=14, d=3, append=True)
            
            # Williams %R
            if include_advanced:
                df.ta.willr(length=14, append=True)
            
            # CCI
            if include_advanced:
                df.ta.cci(length=20, append=True)
            
            # ROC - Rate of Change
            df.ta.roc(length=10, append=True)
            
            # === VOLATILITY INDICATORS ===
            # Bollinger Bands
            df.ta.bbands(length=20, std=2, append=True)
            
            # ATR - Average True Range
            df.ta.atr(length=14, append=True)
            
            # Keltner Channels
            if include_advanced and len(df) >= 20:
                df.ta.kc(length=20, append=True)
            
            # === VOLUME INDICATORS ===
            # OBV - On Balance Volume
            df.ta.obv(append=True)
            
            # VWAP (if intraday)
            try:
                df.ta.vwap(append=True)
            except:
                pass  # VWAP may fail if no proper datetime index
            
            # Volume SMA
            if 'volume' in df.columns:
                df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_sma_20'].replace(0, np.nan)
            
            # MFI - Money Flow Index
            if include_advanced:
                df.ta.mfi(length=14, append=True)
            
            # === CUSTOM FEATURES ===
            df = TechnicalFeatures._add_custom_features(df)
            
            # Fill NaN values
            df = df.ffill().bfill()
            
            logger.debug(f"Added {len(df.columns)} technical features")
            
        except Exception as e:
            logger.error(f"Error calculating technical features: {e}")
        
        return df
    
    @staticmethod
    def _add_custom_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add custom derived features."""
        try:
            # Price position relative to moving averages
            if 'SMA_20' in df.columns and 'close' in df.columns:
                df['price_vs_sma20'] = (df['close'] - df['SMA_20']) / df['SMA_20'] * 100
            
            if 'SMA_50' in df.columns and 'close' in df.columns:
                df['price_vs_sma50'] = (df['close'] - df['SMA_50']) / df['SMA_50'] * 100
            
            # Bollinger Band position (0 to 1)
            if 'BBL_20_2.0' in df.columns and 'BBU_20_2.0' in df.columns:
                bb_range = df['BBU_20_2.0'] - df['BBL_20_2.0']
                df['bb_position'] = (df['close'] - df['BBL_20_2.0']) / bb_range.replace(0, np.nan)
                df['bb_width'] = bb_range / df['BBM_20_2.0'].replace(0, np.nan) * 100
            
            # Returns at different periods
            df['return_1h'] = df['close'].pct_change(1) * 100
            df['return_4h'] = df['close'].pct_change(4) * 100
            df['return_24h'] = df['close'].pct_change(24) * 100
            
            # Volatility measures
            df['volatility_20'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
            
            # Higher highs / Lower lows
            df['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
            df['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
            
            # Candle body analysis
            body = abs(df['close'] - df['open'])
            wick_upper = df['high'] - df[['open', 'close']].max(axis=1)
            wick_lower = df[['open', 'close']].min(axis=1) - df['low']
            
            df['candle_body_pct'] = body / (df['high'] - df['low']).replace(0, np.nan) * 100
            df['is_bullish_candle'] = (df['close'] > df['open']).astype(int)
            
            # Trend strength using ADX if available
            if 'ADX_14' in df.columns:
                df['trend_strong'] = (df['ADX_14'] > 25).astype(int)
            
            # RSI divergence detection (simplified)
            if 'RSI_14' in df.columns:
                price_trend = df['close'].diff(5) > 0
                rsi_trend = df['RSI_14'].diff(5) > 0
                df['rsi_divergence'] = (price_trend != rsi_trend).astype(int)
            
        except Exception as e:
            logger.warning(f"Error adding custom features: {e}")
        
        return df
    
    @staticmethod
    def add_multi_timeframe_features(
        df_main: pd.DataFrame, 
        df_higher: pd.DataFrame,
        suffix: str = "_htf"
    ) -> pd.DataFrame:
        """
        Add features from a higher timeframe.
        
        Args:
            df_main: Main timeframe DataFrame
            df_higher: Higher timeframe DataFrame with indicators
            suffix: Suffix for higher timeframe columns
            
        Returns:
            Main DataFrame with added HTF features
        """
        if df_higher.empty:
            return df_main
            
        # Select key features from higher timeframe
        htf_features = [
            'RSI_14', 'MACD_12_26_9', 'MACDh_12_26_9',
            'SMA_20', 'SMA_50', 'ATRr_14'
        ]
        
        available = [f for f in htf_features if f in df_higher.columns]
        
        if not available:
            return df_main
        
        # Resample higher timeframe to match main timeframe
        df_htf = df_higher[['timestamp'] + available].copy()
        df_htf = df_htf.set_index('timestamp')
        
        # Forward fill to align with main timeframe
        df_htf = df_htf.resample('1H').ffill()
        
        # Rename columns with suffix
        df_htf.columns = [f"{col}{suffix}" for col in df_htf.columns]
        
        # Merge with main DataFrame
        df_main = df_main.set_index('timestamp')
        df_main = df_main.join(df_htf, how='left')
        df_main = df_main.reset_index()
        
        return df_main
    
    @staticmethod
    def get_signal_features(df: pd.DataFrame) -> dict:
        """
        Extract key features for signal generation from latest row.
        
        Args:
            df: DataFrame with technical indicators
            
        Returns:
            Dictionary of feature values
        """
        if df.empty:
            return {}
            
        latest = df.iloc[-1]
        
        features = {
            'rsi_14': latest.get('RSI_14', 50),
            'rsi_7': latest.get('RSI_7', 50),
            'macd': latest.get('MACD_12_26_9', 0),
            'macd_signal': latest.get('MACDs_12_26_9', 0),
            'macd_hist': latest.get('MACDh_12_26_9', 0),
            'bb_position': latest.get('bb_position', 0.5),
            'bb_width': latest.get('bb_width', 0),
            'stoch_k': latest.get('STOCHk_14_3_3', 50),
            'stoch_d': latest.get('STOCHd_14_3_3', 50),
            'atr': latest.get('ATRr_14', 0),
            'adx': latest.get('ADX_14', 0),
            'volume_ratio': latest.get('volume_ratio', 1.0),
            'return_1h': latest.get('return_1h', 0),
            'return_24h': latest.get('return_24h', 0),
            'price': latest.get('close', 0),
        }
        
        return features


def quick_analysis(df: pd.DataFrame) -> str:
    """
    Quick text summary of technical analysis.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Text summary of market conditions
    """
    if df.empty:
        return "No data available"
    
    df = TechnicalFeatures.add_all_features(df, include_advanced=False)
    features = TechnicalFeatures.get_signal_features(df)
    
    summary = []
    
    # RSI
    rsi = features['rsi_14']
    if rsi < 30:
        summary.append(f"RSI oversold ({rsi:.0f})")
    elif rsi > 70:
        summary.append(f"RSI overbought ({rsi:.0f})")
    else:
        summary.append(f"RSI neutral ({rsi:.0f})")
    
    # MACD
    macd_hist = features['macd_hist']
    if macd_hist > 0:
        summary.append("MACD bullish")
    else:
        summary.append("MACD bearish")
    
    # BB Position
    bb_pos = features['bb_position']
    if bb_pos < 0.2:
        summary.append("Near lower BB")
    elif bb_pos > 0.8:
        summary.append("Near upper BB")
    
    return " | ".join(summary)
