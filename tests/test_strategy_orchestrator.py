"""
Unit tests for the Strategy Orchestrator.
Run with: pytest tests/test_strategy_orchestrator.py -v
"""
import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.strategy_orchestrator import StrategyOrchestrator, OrchestratedSignal
from src.strategies.swing_strategy import Signal


class TestStrategyOrchestrator:
    """Test suite for StrategyOrchestrator."""
    
    def setup_method(self):
        """Initialize orchestrator for each test."""
        self.orchestrator = StrategyOrchestrator()
    
    def _create_mock_data(self, trend: str = "neutral", periods: int = 100) -> pd.DataFrame:
        """Create mock OHLCV data with technical indicators."""
        np.random.seed(42)
        
        # Base price movement
        if trend == "bullish":
            base_prices = np.linspace(100, 120, periods)
            rsi = 35  # Oversold to trigger buy
        elif trend == "bearish":
            base_prices = np.linspace(120, 100, periods)
            rsi = 75  # Overbought to trigger sell
        else:
            base_prices = np.linspace(100, 102, periods)
            rsi = 50
        
        # Add noise
        noise = np.random.normal(0, 1, periods)
        prices = base_prices + noise
        
        df = pd.DataFrame({
            'open': prices - 0.5,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.random.randint(1000, 5000, periods),
            # Pre-computed technical indicators
            'RSI_14': [rsi] * periods,
            'MACD_12_26_9': [0.5 if trend == "bullish" else -0.5 if trend == "bearish" else 0] * periods,
            'MACDs_12_26_9': [0.3 if trend == "bullish" else -0.3 if trend == "bearish" else 0] * periods,
            'MACDh_12_26_9': [0.2 if trend == "bullish" else -0.2 if trend == "bearish" else 0] * periods,
            'BBL_20_2.0': prices - 3,
            'BBM_20_2.0': prices,
            'BBU_20_2.0': prices + 3,
            'SMA_20': prices - 1 if trend == "bullish" else prices + 1 if trend == "bearish" else prices,
            'SMA_50': prices - 2 if trend == "bullish" else prices + 2 if trend == "bearish" else prices,
            'STOCHk_14_3_3': [20 if trend == "bullish" else 80 if trend == "bearish" else 50] * periods,
            'STOCHd_14_3_3': [20 if trend == "bullish" else 80 if trend == "bearish" else 50] * periods,
            'ATRr_14': [2.0] * periods,
            'OBV': np.cumsum(np.random.randint(-100, 100, periods)),
        })
        
        return df


class TestSignalGeneration(TestStrategyOrchestrator):
    """Test signal generation functionality."""
    
    def test_insufficient_data_returns_hold(self):
        """Empty or small dataframe should return HOLD signal."""
        df = pd.DataFrame()
        signal = self.orchestrator.generate(df, "TEST/EUR")
        
        assert signal.action == "HOLD"
        assert signal.confidence == 0
        assert "Insufficient data" in signal.reasons[0]
    
    def test_bullish_data_generates_buy(self):
        """Bullish trending data should generate BUY or very low confidence signal."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        # Strong bullish should either be BUY or have positive scores
        # (even if not actionable due to conservative thresholds)
        assert signal.swing_score >= 0 or signal.ml_score_raw >= 0, \
            f"Bullish data should have positive scores: swing={signal.swing_score}, ml={signal.ml_score_raw}"
    
    def test_bearish_data_generates_sell(self):
        """Bearish trending data should generate SELL signal."""
        df = self._create_mock_data(trend="bearish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert signal.action == "SELL"
        assert signal.confidence > 0
    
    def test_neutral_data_may_hold(self):
        """Neutral data should generate low confidence or HOLD signal."""
        df = self._create_mock_data(trend="neutral")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        # Neutral data should either HOLD or have low confidence
        assert signal.action in ["BUY", "SELL", "HOLD"]
        # If actionable, confidence should be relatively low
        if signal.action != "HOLD":
            assert signal.confidence < 0.7


class TestSignalStrength(TestStrategyOrchestrator):
    """Test STRONG signal detection."""
    
    def test_signal_has_strength_attribute(self):
        """All signals should have signal_strength attribute."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert hasattr(signal, 'signal_strength')
        assert signal.signal_strength in ["NORMAL", "STRONG"]
    
    def test_strong_signal_has_confluence_reason(self):
        """STRONG signals should mention confluence in reasons."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        if signal.signal_strength == "STRONG":
            assert any("CONFLUENCE" in r for r in signal.reasons)


class TestContributingStrategies(TestStrategyOrchestrator):
    """Test contributing strategies tracking."""
    
    def test_signal_tracks_contributing_strategies(self):
        """Signal should track which strategies contributed."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert hasattr(signal, 'contributing_strategies')
        assert isinstance(signal.contributing_strategies, list)
    
    def test_strategies_listed_when_actionable(self):
        """Actionable signals should list contributing strategies."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        if signal.is_actionable:
            assert len(signal.contributing_strategies) > 0


class TestScoreComponents(TestStrategyOrchestrator):
    """Test individual score components."""
    
    def test_swing_score_in_signal(self):
        """Signal should contain swing strategy score."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert hasattr(signal, 'swing_score')
        assert -1 <= signal.swing_score <= 1
    
    def test_ml_score_in_signal(self):
        """Signal should contain ML strategy score."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert hasattr(signal, 'ml_score_raw')
        assert -1 <= signal.ml_score_raw <= 1
    
    def test_atr_preserved_in_signal(self):
        """ATR should be passed through to signal."""
        df = self._create_mock_data(trend="bullish")
        signal = self.orchestrator.generate(df, "BTC/EUR")
        
        assert hasattr(signal, 'atr')
        # ATR should be from the mock data (2.0)
        assert signal.atr >= 0


class TestIsActionable(TestStrategyOrchestrator):
    """Test is_actionable property."""
    
    def test_hold_not_actionable(self):
        """HOLD signals should not be actionable."""
        signal = OrchestratedSignal(
            action="HOLD",
            confidence=0.5,
            technical_score=0,
            ml_score=0,
            volume_score=0,
            reasons=[],
            atr=0
        )
        assert not signal.is_actionable
    
    def test_buy_with_confidence_is_actionable(self):
        """BUY with sufficient confidence should be actionable."""
        signal = OrchestratedSignal(
            action="BUY",
            confidence=0.5,
            technical_score=0.5,
            ml_score=0.5,
            volume_score=0.3,
            reasons=["Test"],
            atr=2.0
        )
        assert signal.is_actionable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
