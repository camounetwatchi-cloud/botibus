"""
Unit tests for the Fee Calculator module.
Run with: pytest tests/test_fee_calculator.py -v
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.fee_calculator import FeeCalculator, fee_calculator
from src.config.settings import settings


class TestEntryFees:
    """Test entry fee calculations."""
    
    def setup_method(self):
        self.fc = FeeCalculator()
    
    def test_entry_fees_margin(self):
        """Margin trade should have taker fee + opening fee + slippage."""
        trade_value = 1000.0  # €1000 position
        
        fees = self.fc.calculate_entry_fees(trade_value, is_margin=True)
        
        # Expected: 0.1% taker + 0.02% margin opening + 0.05% slippage = 0.17%
        expected_trading = 1000 * 0.001  # €1.00
        expected_margin = 1000 * 0.0002  # €0.20
        expected_slippage = 1000 * 0.0005  # €0.50
        expected_total = 1.70  # Updated for slippage
        
        assert abs(fees['trading_fee'] - expected_trading) < 0.001
        assert abs(fees['margin_fee'] - expected_margin) < 0.001
        assert abs(fees['slippage'] - expected_slippage) < 0.001
        assert abs(fees['total'] - expected_total) < 0.001
    
    def test_entry_fees_spot(self):
        """Spot trade should have only taker fee + slippage."""
        trade_value = 1000.0
        
        fees = self.fc.calculate_entry_fees(trade_value, is_margin=False)
        
        expected_trading = 1000 * 0.001  # €1.00
        expected_slippage = 1000 * 0.0005  # €0.50
        expected_total = expected_trading + expected_slippage  # €1.50
        
        assert abs(fees['trading_fee'] - expected_trading) < 0.001
        assert fees['margin_fee'] == 0.0
        assert abs(fees['total'] - expected_total) < 0.001


class TestExitFees:
    """Test exit fee calculations."""
    
    def setup_method(self):
        self.fc = FeeCalculator()
    
    def test_exit_fees(self):
        """Exit fee should be taker fee = 0.1%."""
        trade_value = 1000.0
        
        fee = self.fc.calculate_exit_fees(trade_value)
        
        expected = 1000 * 0.001  # €1.00
        assert abs(fee - expected) < 0.001


class TestRolloverFees:
    """Test rollover fee calculations."""
    
    def setup_method(self):
        self.fc = FeeCalculator()
    
    def test_rollover_fees_under_4h(self):
        """Position held less than 4 hours should have no rollover fee."""
        trade_value = 1000.0
        entry_time = datetime.now() - timedelta(hours=3, minutes=59)
        
        fee = self.fc.calculate_rollover_fees(trade_value, entry_time)
        
        assert fee == 0.0
    
    def test_rollover_fees_4h(self):
        """Position held 4-8 hours should have 1 rollover period = 0.02%."""
        trade_value = 1000.0
        entry_time = datetime.now() - timedelta(hours=5)
        
        fee = self.fc.calculate_rollover_fees(trade_value, entry_time)
        
        expected = 1000 * 0.0002 * 1  # €0.20
        assert abs(fee - expected) < 0.001
    
    def test_rollover_fees_8h(self):
        """Position held 8-12 hours should have 2 rollover periods = 0.04%."""
        trade_value = 1000.0
        entry_time = datetime.now() - timedelta(hours=9)
        
        fee = self.fc.calculate_rollover_fees(trade_value, entry_time)
        
        expected = 1000 * 0.0002 * 2  # €0.40
        assert abs(fee - expected) < 0.001
    
    def test_rollover_fees_24h(self):
        """Position held 24+ hours should have 6 rollover periods = 0.12%."""
        trade_value = 1000.0
        entry_time = datetime.now() - timedelta(hours=25)
        
        fee = self.fc.calculate_rollover_fees(trade_value, entry_time)
        
        expected = 1000 * 0.0002 * 6  # €1.20
        assert abs(fee - expected) < 0.001


class TestTotalFees:
    """Test total fee calculations."""
    
    def setup_method(self):
        self.fc = FeeCalculator()
    
    def test_total_fees_calculation(self):
        """Total fees should be sum of all components."""
        entry_fee = 1.20
        exit_fee = 1.00
        rollover_fee = 0.40
        
        total = self.fc.calculate_total_fees(entry_fee, exit_fee, rollover_fee)
        
        assert abs(total - 2.60) < 0.001


class TestCompleteTradeScenario:
    """Test complete trade lifecycle fee calculation."""
    
    def setup_method(self):
        self.fc = FeeCalculator()
    
    def test_short_trade(self):
        """Trade lasting 2 hours should have entry + exit fees only."""
        entry_price = 95000.0  # BTC at €95,000
        exit_price = 96000.0
        amount = 0.01  # 0.01 BTC
        entry_time = datetime.now() - timedelta(hours=2)
        
        fees = self.fc.calculate_all_fees_for_trade(
            entry_price, exit_price, amount, entry_time, is_margin=True
        )
        
        # Entry value: €950
        # Exit value: €960
        # Entry fee: €950 * 0.12% = €1.14
        # Exit fee: €960 * 0.1% = €0.96
        # Rollover: €0 (under 4h)
        # Total: €2.10
        
        assert fees['entry_fee'] > 0
        assert fees['exit_fee'] > 0
        assert fees['rollover_fee'] == 0
        assert fees['total_fees'] == fees['entry_fee'] + fees['exit_fee']
    
    def test_overnight_trade(self):
        """Trade lasting 12 hours should include rollover fees."""
        entry_price = 95000.0
        exit_price = 96000.0
        amount = 0.01
        entry_time = datetime.now() - timedelta(hours=12)
        
        fees = self.fc.calculate_all_fees_for_trade(
            entry_price, exit_price, amount, entry_time, is_margin=True
        )
        
        # 12 hours = 3 rollover periods
        # Rollover: €950 * 0.02% * 3 = €0.57
        
        assert fees['rollover_fee'] > 0
        assert fees['total_fees'] > fees['entry_fee'] + fees['exit_fee']


class TestSettingsIntegration:
    """Test that fee calculator uses correct settings."""
    
    def test_uses_settings_values(self):
        """Fee calculator should use values from settings."""
        fc = FeeCalculator()
        
        assert fc.taker_fee == settings.TAKER_FEE
        assert fc.margin_opening_fee == settings.MARGIN_OPENING_FEE
        assert fc.margin_rollover_fee == settings.MARGIN_ROLLOVER_FEE
        assert fc.rollover_interval_hours == settings.ROLLOVER_INTERVAL_HOURS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
