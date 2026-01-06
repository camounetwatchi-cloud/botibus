"""
Strategy Orchestrator - Multi-Strategy Ensemble for Aggressive Trading.

Combines multiple strategy signals with weighted voting for optimal
trading decisions. Supports STRONG_BUY/STRONG_SELL signals when
strategies agree.
"""
import numpy as np
import pandas as pd
from typing import Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger

from src.config.settings import settings
from src.ml.signal_generator import SignalGenerator, MLSignal
from src.strategies.swing_strategy import SwingStrategy, Signal


@dataclass
class OrchestratedSignal(MLSignal):
    """Extended signal with strategy-specific metadata."""
    swing_score: float = 0.0
    ml_score_raw: float = 0.0
    signal_strength: str = "NORMAL"  # NORMAL, STRONG
    contributing_strategies: List[str] = None
    
    def __post_init__(self):
        if self.contributing_strategies is None:
            self.contributing_strategies = []


class StrategyOrchestrator:
    """
    Multi-strategy ensemble that combines:
    - SwingStrategy: Technical indicator confluence (50%)
    - SignalGenerator: ML-based pattern recognition (50%)
    
    Produces STRONG signals when both strategies agree with high confidence.
    """
    
    # Strategy weights (must sum to 1.0)
    WEIGHTS = {
        'swing': 0.50,
        'ml': 0.50,
    }
    
    # Thresholds
    CONFLUENCE_THRESHOLD = 0.60  # Both strategies must exceed this for STRONG
    STRONG_SIGNAL_THRESHOLD = 0.70  # Combined score for STRONG signal
    MIN_ACTIONABLE = 0.15  # Minimum score to generate BUY/SELL
    
    def __init__(self):
        """Initialize with both strategy components."""
        self.swing_strategy = SwingStrategy(
            rsi_oversold=30,
            rsi_overbought=70,
            bb_squeeze_threshold=0.1,
            min_volume_ratio=1.2
        )
        self.signal_generator = SignalGenerator()
        
        logger.info("StrategyOrchestrator initialized with SwingStrategy + SignalGenerator")
    
    def generate(self, df: pd.DataFrame, symbol: str = "") -> OrchestratedSignal:
        """
        Generate trading signal by combining multiple strategies.
        
        Args:
            df: DataFrame with OHLCV and technical indicators
            symbol: Symbol being analyzed (for logging)
            
        Returns:
            OrchestratedSignal with combined action and confidence
        """
        if df.empty or len(df) < 50:
            return self._empty_signal("Insufficient data")
        
        reasons = []
        contributing = []
        
        # === 1. SwingStrategy Analysis ===
        swing_signal = self.swing_strategy.analyze(df)
        swing_score = 0.0
        
        if swing_signal:
            # Convert Signal enum to score [-1, 1]
            swing_score = self._signal_to_score(swing_signal.signal)
            
            if swing_signal.is_actionable:
                contributing.append("SwingStrategy")
                reasons.extend(swing_signal.reasons[:2])
        
        # === 2. SignalGenerator (ML) Analysis ===
        ml_signal = self.signal_generator.generate(df, symbol)
        ml_score = 0.0
        
        if ml_signal:
            # Convert ML action to score [-1, 1]
            if ml_signal.action == "BUY":
                ml_score = ml_signal.confidence
            elif ml_signal.action == "SELL":
                ml_score = -ml_signal.confidence
            
            if ml_signal.is_actionable:
                contributing.append("SignalGenerator")
                reasons.extend(ml_signal.reasons[:2])
        
        # === 3. Weighted Ensemble ===
        combined_score = (
            swing_score * self.WEIGHTS['swing'] +
            ml_score * self.WEIGHTS['ml']
        )
        
        # Normalize to [-1, 1]
        combined_score = np.clip(combined_score, -1, 1)
        confidence = abs(combined_score)
        
        # === 4. Determine Action and Strength ===
        action = "HOLD"
        signal_strength = "NORMAL"
        
        if combined_score >= self.MIN_ACTIONABLE:
            action = "BUY"
        elif combined_score <= -self.MIN_ACTIONABLE:
            action = "SELL"
        
        # Check for STRONG signal (confluence)
        if action != "HOLD":
            swing_agrees = (swing_score > 0 and action == "BUY") or (swing_score < 0 and action == "SELL")
            ml_agrees = (ml_score > 0 and action == "BUY") or (ml_score < 0 and action == "SELL")
            
            both_confident = (
                abs(swing_score) >= self.CONFLUENCE_THRESHOLD and
                abs(ml_score) >= self.CONFLUENCE_THRESHOLD
            )
            
            if swing_agrees and ml_agrees and both_confident:
                signal_strength = "STRONG"
                reasons.insert(0, f"CONFLUENCE: Both strategies agree ({action})")
        
        # Get ATR from ML signal or calculate
        atr = getattr(ml_signal, 'atr', 0) if ml_signal else 0
        
        signal = OrchestratedSignal(
            action=action,
            confidence=confidence,
            technical_score=swing_score,
            ml_score=ml_score,
            volume_score=ml_signal.volume_score if ml_signal else 0,
            reasons=reasons[:5],
            atr=atr,
            swing_score=swing_score,
            ml_score_raw=ml_score,
            signal_strength=signal_strength,
            contributing_strategies=contributing
        )
        
        if signal.is_actionable:
            strength_emoji = "⚡" if signal_strength == "STRONG" else ""
            logger.info(
                f"[{symbol}] {strength_emoji}{signal_strength} Signal: {action} "
                f"(conf: {confidence:.2f}) | Swing: {swing_score:.2f}, ML: {ml_score:.2f} | "
                f"Strategies: {', '.join(contributing)}"
            )
        
        return signal
    
    def _signal_to_score(self, signal: Signal) -> float:
        """Convert Signal enum to score in [-1, 1]."""
        mapping = {
            Signal.STRONG_BUY: 1.0,
            Signal.BUY: 0.6,
            Signal.HOLD: 0.0,
            Signal.SELL: -0.6,
            Signal.STRONG_SELL: -1.0,
        }
        return mapping.get(signal, 0.0)
    
    def _empty_signal(self, reason: str) -> OrchestratedSignal:
        """Return empty HOLD signal."""
        return OrchestratedSignal(
            action="HOLD",
            confidence=0,
            technical_score=0,
            ml_score=0,
            volume_score=0,
            reasons=[reason],
            atr=0,
            swing_score=0,
            ml_score_raw=0,
            signal_strength="NORMAL",
            contributing_strategies=[]
        )


def create_strategy_orchestrator() -> StrategyOrchestrator:
    """Factory function to create strategy orchestrator."""
    return StrategyOrchestrator()
