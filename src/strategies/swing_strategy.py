"""
Swing Trading Strategy based on technical indicator confluence.

This strategy generates BUY/SELL/HOLD signals based on multiple
technical indicators with weighted scoring.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class Signal(Enum):
    """Trading signal types."""
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class TradingSignal:
    """Container for trading signal with metadata."""
    signal: Signal
    confidence: float
    reasons: list
    indicators: Dict[str, float]
    
    @property
    def action(self) -> str:
        """Get the action string."""
        if self.signal in (Signal.STRONG_BUY, Signal.BUY):
            return "BUY"
        elif self.signal in (Signal.STRONG_SELL, Signal.SELL):
            return "SELL"
        return "HOLD"
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal meets confidence threshold."""
        return self.signal != Signal.HOLD and self.confidence >= 0.55


class SwingStrategy:
    """
    Multi-indicator Swing Trading Strategy.
    
    Combines multiple technical indicators with weighted scoring
    to generate high-confidence trading signals.
    """
    
    # Indicator weights for scoring
    WEIGHTS = {
        'rsi': 0.15,
        'macd': 0.20,
        'bollinger': 0.15,
        'trend': 0.20,
        'volume': 0.10,
        'momentum': 0.10,
        'atr_filter': 0.10,
    }
    
    # RSI thresholds
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_STRONG_OVERSOLD = 20
    RSI_STRONG_OVERBOUGHT = 80
    
    # Minimum confidence for trades
    MIN_CONFIDENCE = 0.55
    
    def __init__(self, 
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 bb_squeeze_threshold: float = 0.1,
                 min_volume_ratio: float = 1.2):
        """
        Initialize swing strategy.
        
        Args:
            rsi_oversold: RSI level considered oversold
            rsi_overbought: RSI level considered overbought
            bb_squeeze_threshold: Bollinger Band width for squeeze detection
            min_volume_ratio: Minimum volume vs avg for confirmation
        """
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_squeeze_threshold = bb_squeeze_threshold
        self.min_volume_ratio = min_volume_ratio
        
    def analyze(self, df: pd.DataFrame) -> Optional[TradingSignal]:
        """
        Analyze OHLCV data with technical indicators and generate signal.
        
        Args:
            df: DataFrame with OHLCV + technical indicators
            
        Returns:
            TradingSignal with confidence score and reasoning
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for analysis")
            return None
            
        # Get latest row for analysis
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        scores = {}
        reasons = []
        indicators = {}
        
        # === 1. RSI Analysis ===
        rsi_score, rsi_reason = self._analyze_rsi(latest, df)
        scores['rsi'] = rsi_score
        if rsi_reason:
            reasons.append(rsi_reason)
        indicators['RSI'] = latest.get('RSI_14', 50)
        
        # === 2. MACD Analysis ===
        macd_score, macd_reason = self._analyze_macd(latest, prev, df)
        scores['macd'] = macd_score
        if macd_reason:
            reasons.append(macd_reason)
        indicators['MACD'] = latest.get('MACD_12_26_9', 0)
        indicators['MACD_Signal'] = latest.get('MACDs_12_26_9', 0)
        
        # === 3. Bollinger Bands Analysis ===
        bb_score, bb_reason = self._analyze_bollinger(latest, df)
        scores['bollinger'] = bb_score
        if bb_reason:
            reasons.append(bb_reason)
        indicators['BB_Upper'] = latest.get('BBU_20_2.0', 0)
        indicators['BB_Lower'] = latest.get('BBL_20_2.0', 0)
        
        # === 4. Trend Analysis (SMA) ===
        trend_score, trend_reason = self._analyze_trend(latest, df)
        scores['trend'] = trend_score
        if trend_reason:
            reasons.append(trend_reason)
        indicators['SMA_20'] = latest.get('SMA_20', 0)
        indicators['SMA_50'] = latest.get('SMA_50', 0)
        
        # === 5. Volume Confirmation ===
        volume_score, volume_reason = self._analyze_volume(df)
        scores['volume'] = volume_score
        if volume_reason:
            reasons.append(volume_reason)
        indicators['Volume_Ratio'] = self._get_volume_ratio(df)
        
        # === 6. Momentum Analysis ===
        momentum_score, momentum_reason = self._analyze_momentum(df)
        scores['momentum'] = momentum_score
        if momentum_reason:
            reasons.append(momentum_reason)
            
        # === 7. ATR Volatility Filter ===
        atr_score, atr_reason = self._analyze_volatility(latest, df)
        scores['atr_filter'] = atr_score
        if atr_reason:
            reasons.append(atr_reason)
        indicators['ATR'] = latest.get('ATRr_14', 0)
        
        # === Calculate Weighted Score ===
        total_score = sum(
            scores[k] * self.WEIGHTS[k] 
            for k in scores
        )
        
        # Normalize to [-1, 1]
        normalized_score = np.clip(total_score / sum(self.WEIGHTS.values()), -1, 1)
        
        # Calculate confidence (how strong is the signal)
        confidence = abs(normalized_score)
        
        # Determine signal type
        if normalized_score >= 0.6:
            signal = Signal.STRONG_BUY
        elif normalized_score >= 0.3:
            signal = Signal.BUY
        elif normalized_score <= -0.6:
            signal = Signal.STRONG_SELL
        elif normalized_score <= -0.3:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
            
        return TradingSignal(
            signal=signal,
            confidence=confidence,
            reasons=reasons,
            indicators=indicators
        )
    
    def _analyze_rsi(self, latest: pd.Series, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze RSI for overbought/oversold conditions."""
        rsi = latest.get('RSI_14', 50)
        
        if pd.isna(rsi):
            return 0, ""
            
        if rsi <= self.RSI_STRONG_OVERSOLD:
            return 1.0, f"RSI strongly oversold ({rsi:.1f})"
        elif rsi <= self.rsi_oversold:
            return 0.7, f"RSI oversold ({rsi:.1f})"
        elif rsi >= self.RSI_STRONG_OVERBOUGHT:
            return -1.0, f"RSI strongly overbought ({rsi:.1f})"
        elif rsi >= self.rsi_overbought:
            return -0.7, f"RSI overbought ({rsi:.1f})"
        elif 40 <= rsi <= 60:
            return 0, ""  # Neutral zone
        elif rsi < 40:
            return 0.3, f"RSI approaching oversold ({rsi:.1f})"
        else:
            return -0.3, f"RSI approaching overbought ({rsi:.1f})"
    
    def _analyze_macd(self, latest: pd.Series, prev: pd.Series, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze MACD for crossovers and momentum."""
        macd = latest.get('MACD_12_26_9', 0)
        signal = latest.get('MACDs_12_26_9', 0)
        hist = latest.get('MACDh_12_26_9', 0)
        
        prev_hist = prev.get('MACDh_12_26_9', 0)
        
        if pd.isna(macd) or pd.isna(signal):
            return 0, ""
        
        score = 0
        reason = ""
        
        # MACD crosses signal line upward (bullish)
        if prev_hist < 0 and hist >= 0:
            score = 0.8
            reason = "MACD bullish crossover"
        # MACD crosses signal line downward (bearish)
        elif prev_hist > 0 and hist <= 0:
            score = -0.8
            reason = "MACD bearish crossover"
        # MACD histogram growing (bullish momentum)
        elif hist > 0 and hist > prev_hist:
            score = 0.4
            reason = "MACD bullish momentum"
        # MACD histogram shrinking (bearish momentum)
        elif hist < 0 and hist < prev_hist:
            score = -0.4
            reason = "MACD bearish momentum"
        # MACD above zero line
        elif macd > 0:
            score = 0.2
        # MACD below zero line
        else:
            score = -0.2
            
        return score, reason
    
    def _analyze_bollinger(self, latest: pd.Series, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze Bollinger Bands for mean reversion and breakouts."""
        close = latest.get('close', 0)
        upper = latest.get('BBU_20_2.0', 0)
        lower = latest.get('BBL_20_2.0', 0)
        middle = latest.get('BBM_20_2.0', 0)
        
        if pd.isna(upper) or pd.isna(lower) or upper == lower:
            return 0, ""
            
        # Calculate position within bands
        bb_percent = (close - lower) / (upper - lower) if upper != lower else 0.5
        
        if bb_percent <= 0.05:
            return 0.9, "Price at lower Bollinger Band (potential bounce)"
        elif bb_percent <= 0.2:
            return 0.5, "Price near lower Bollinger Band"
        elif bb_percent >= 0.95:
            return -0.9, "Price at upper Bollinger Band (potential reversal)"
        elif bb_percent >= 0.8:
            return -0.5, "Price near upper Bollinger Band"
        else:
            return 0, ""
    
    def _analyze_trend(self, latest: pd.Series, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze trend using moving averages."""
        close = latest.get('close', 0)
        sma20 = latest.get('SMA_20', 0)
        sma50 = latest.get('SMA_50', 0)
        sma200 = latest.get('SMA_200', 0)
        
        if pd.isna(sma20) or pd.isna(sma50):
            return 0, ""
            
        score = 0
        reasons = []
        
        # Price position relative to MAs
        if close > sma20 > sma50:
            score += 0.5
            reasons.append("Price above SMAs (uptrend)")
        elif close < sma20 < sma50:
            score -= 0.5
            reasons.append("Price below SMAs (downtrend)")
            
        # Golden/Death cross detection
        if len(df) >= 2:
            prev_sma20 = df.iloc[-2].get('SMA_20', 0)
            prev_sma50 = df.iloc[-2].get('SMA_50', 0)
            
            if prev_sma20 < prev_sma50 and sma20 >= sma50:
                score += 0.8
                reasons.append("Golden Cross forming")
            elif prev_sma20 > prev_sma50 and sma20 <= sma50:
                score -= 0.8
                reasons.append("Death Cross forming")
        
        return np.clip(score, -1, 1), " | ".join(reasons) if reasons else ""
    
    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze volume for confirmation."""
        if 'volume' not in df.columns or len(df) < 20:
            return 0, ""
            
        latest_vol = df.iloc[-1]['volume']
        avg_vol = df['volume'].tail(20).mean()
        
        if avg_vol == 0:
            return 0, ""
            
        vol_ratio = latest_vol / avg_vol
        
        if vol_ratio >= 2.0:
            return 0.8, f"High volume confirmation ({vol_ratio:.1f}x avg)"
        elif vol_ratio >= self.min_volume_ratio:
            return 0.4, f"Above average volume ({vol_ratio:.1f}x)"
        elif vol_ratio < 0.5:
            return -0.3, "Low volume - weak signal"
        else:
            return 0, ""
    
    def _analyze_momentum(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze short-term momentum."""
        if len(df) < 5:
            return 0, ""
            
        # Calculate 5-period return
        current = df.iloc[-1]['close']
        past = df.iloc[-5]['close']
        
        if past == 0:
            return 0, ""
            
        momentum = (current - past) / past * 100
        
        if momentum >= 3:
            return 0.6, f"Strong bullish momentum (+{momentum:.1f}%)"
        elif momentum >= 1:
            return 0.3, f"Bullish momentum (+{momentum:.1f}%)"
        elif momentum <= -3:
            return -0.6, f"Strong bearish momentum ({momentum:.1f}%)"
        elif momentum <= -1:
            return -0.3, f"Bearish momentum ({momentum:.1f}%)"
        else:
            return 0, ""
    
    def _analyze_volatility(self, latest: pd.Series, df: pd.DataFrame) -> Tuple[float, str]:
        """Analyze ATR for volatility filter."""
        atr = latest.get('ATRr_14', 0)
        close = latest.get('close', 0)
        
        if pd.isna(atr) or close == 0:
            return 0, ""
            
        # ATR as percentage of price
        atr_pct = (atr / close) * 100
        
        # Ideal volatility range for swing trading: 1-4%
        if 1 <= atr_pct <= 4:
            return 0.5, f"Good volatility for swing ({atr_pct:.1f}%)"
        elif atr_pct > 6:
            return -0.5, f"High volatility risk ({atr_pct:.1f}%)"
        elif atr_pct < 0.5:
            return -0.3, "Low volatility - limited opportunity"
        else:
            return 0, ""
    
    def _get_volume_ratio(self, df: pd.DataFrame) -> float:
        """Calculate volume ratio vs average."""
        if 'volume' not in df.columns or len(df) < 20:
            return 1.0
            
        latest_vol = df.iloc[-1]['volume']
        avg_vol = df['volume'].tail(20).mean()
        
        if avg_vol == 0:
            return 1.0
            
        return latest_vol / avg_vol


def calculate_position_size(
    balance: float,
    price: float,
    risk_percent: float = 0.02,
    stop_loss_percent: float = 0.025,
    max_position_percent: float = 0.15
) -> float:
    """
    Calculate position size based on risk management rules.
    
    Args:
        balance: Available balance in USDT
        price: Current asset price
        risk_percent: Percentage of balance to risk per trade (2%)
        stop_loss_percent: Stop loss percentage (2.5%)
        max_position_percent: Maximum position as % of balance (15%)
        
    Returns:
        Position size in asset units
    """
    # Risk-based position size
    risk_amount = balance * risk_percent
    position_value_from_risk = risk_amount / stop_loss_percent
    
    # Max position constraint
    max_position_value = balance * max_position_percent
    
    # Use the smaller of the two
    position_value = min(position_value_from_risk, max_position_value)
    
    # Minimum position value check ($100)
    if position_value < 100:
        return 0
        
    position_size = position_value / price
    
    return position_size
