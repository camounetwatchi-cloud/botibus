"""
Unit tests for the enhanced Risk Manager with dynamic TP and trailing stops.
Run with: pytest tests/test_risk_manager.py -v
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.risk_manager import RiskManager, RiskConfig
from src.config.settings import settings


class TestRiskManagerPositionLimits:
    """Test position limits for paper trading."""
    
    def test_max_positions_paper_trading(self):
        """Verify that 30 positions are allowed in paper trading mode."""
        assert settings.MAX_OPEN_POSITIONS == 30, "Paper trading should allow 30 positions"
    
    def test_max_positions_live_trading(self):
        """Verify that live trading is limited to 15 positions for safety."""
        assert settings.MAX_OPEN_POSITIONS_LIVE == 15, "Live trading should be limited to 15"


class TestDynamicTakeProfit:
    """Test dynamic take-profit based on volatility."""
    
    def setup_method(self):
        self.rm = RiskManager(RiskConfig())
    
    def test_low_volatility_tp(self):
        """Low volatility (ATR < 1.5%) should use 3% TP."""
        price = 50000  # BTC price
        atr = 500  # 1% ATR (low volatility)
        
        tp = self.rm.calculate_dynamic_take_profit(price, atr)
        tp_pct = (tp - price) / price
        
        assert abs(tp_pct - 0.03) < 0.001, f"Low vol TP should be ~3%, got {tp_pct*100:.1f}%"
    
    def test_normal_volatility_tp(self):
        """Normal volatility (1.5-3% ATR) should use 4.5% TP."""
        price = 50000
        atr = 1000  # 2% ATR (normal volatility)
        
        tp = self.rm.calculate_dynamic_take_profit(price, atr)
        tp_pct = (tp - price) / price
        
        assert abs(tp_pct - 0.045) < 0.001, f"Normal vol TP should be ~4.5%, got {tp_pct*100:.1f}%"
    
    def test_high_volatility_tp(self):
        """High volatility (ATR > 3%) should use 6% TP."""
        price = 50000
        atr = 2000  # 4% ATR (high volatility)
        
        tp = self.rm.calculate_dynamic_take_profit(price, atr)
        tp_pct = (tp - price) / price
        
        assert abs(tp_pct - 0.06) < 0.001, f"High vol TP should be ~6%, got {tp_pct*100:.1f}%"
    
    def test_no_atr_default_tp(self):
        """When no ATR available, use default TP."""
        price = 50000
        atr = 0  # No ATR
        
        tp = self.rm.calculate_dynamic_take_profit(price, atr)
        tp_pct = (tp - price) / price
        
        assert abs(tp_pct - settings.DEFAULT_TAKE_PROFIT) < 0.001


class TestTrailingStop:
    """Test trailing stop activation and triggering."""
    
    def setup_method(self):
        self.rm = RiskManager(RiskConfig())
    
    def test_trailing_not_active_below_threshold(self):
        """Trailing stop should not be active below 2% profit."""
        entry = 50000
        current = 50500  # 1% profit
        peak = 50500
        
        should_close, _, reason = self.rm.calculate_trailing_stop(entry, current, peak, 'buy')
        
        assert not should_close
        assert "not yet active" in reason.lower()
    
    def test_trailing_active_above_threshold(self):
        """Trailing stop should be active above 2% profit."""
        entry = 50000
        peak = 51500  # 3% peak profit
        current = 51400  # Still within trailing distance
        
        should_close, trail_price, reason = self.rm.calculate_trailing_stop(entry, current, peak, 'buy')
        
        assert not should_close
        assert "active" in reason.lower()
        assert trail_price > 0
    
    def test_trailing_triggered(self):
        """Trailing stop should trigger when price drops below trail level."""
        entry = 50000
        peak = 52000  # 4% peak profit
        current = 51400  # Dropped 1.15% from peak (exceeds 1% trailing distance)
        
        should_close, _, reason = self.rm.calculate_trailing_stop(entry, current, peak, 'buy')
        
        assert should_close
        assert "hit" in reason.lower()


class TestConfidenceBasedSizing:
    """Test position sizing based on signal confidence."""
    
    def setup_method(self):
        self.rm = RiskManager(RiskConfig())
        self.balance = 1000
        self.price = 50000
    
    def test_low_confidence_sizing(self):
        """50-60% confidence should use 0.5x multiplier."""
        mult = self.rm._get_confidence_multiplier(0.55)
        assert mult == settings.CONFIDENCE_MULTIPLIER_LOW  # 0.5
    
    def test_medium_confidence_sizing(self):
        """60-70% confidence should use 0.8x multiplier."""
        mult = self.rm._get_confidence_multiplier(0.65)
        assert mult == settings.CONFIDENCE_MULTIPLIER_MEDIUM  # 0.8
    
    def test_high_confidence_sizing(self):
        """70-85% confidence should use 1.0x multiplier."""
        mult = self.rm._get_confidence_multiplier(0.75)
        assert mult == settings.CONFIDENCE_MULTIPLIER_HIGH  # 1.0
    
    def test_very_high_confidence_sizing(self):
        """85%+ confidence should use 1.2x multiplier."""
        mult = self.rm._get_confidence_multiplier(0.90)
        assert mult == settings.CONFIDENCE_MULTIPLIER_VERY_HIGH  # 1.2
    
    def test_below_threshold_no_trade(self):
        """Below MIN_SIGNAL_CONFIDENCE (20%) should return 0."""
        mult = self.rm._get_confidence_multiplier(0.15)  # 15% is below 20% threshold
        assert mult == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
