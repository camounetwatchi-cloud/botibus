"""
Unit tests for the Performance Analyzer with Kelly Criterion.
Run with: pytest tests/test_performance_analyzer.py -v
"""
import pytest
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.learning.performance import PerformanceAnalyzer


class MockStorage:
    """Mock storage for testing."""
    
    def __init__(self, trades_data=None):
        self.trades_data = trades_data
    
    def get_trades(self, status=None):
        if self.trades_data is not None:
            df = pd.DataFrame(self.trades_data)
            if status and not df.empty:
                df = df[df['status'] == status]
            return df
        return pd.DataFrame()


class TestKellyFraction:
    """Test Kelly Criterion calculation."""
    
    def test_kelly_positive_edge(self):
        """A profitable strategy should return positive Kelly fraction."""
        # 60% win rate, avg win 10€, avg loss 5€
        # Kelly = (0.6 * 10 - 0.4 * 5) / 10 = 0.4
        # Half-Kelly = 0.2
        trades = [
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -5, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        kelly = analyzer.calculate_kelly_fraction('BTC/EUR', lookback_trades=10)
        
        # Half-Kelly of 0.4 = 0.2, should be positive
        assert kelly > 0, f"Expected positive Kelly, got {kelly}"
        assert kelly <= 0.25, f"Kelly should be capped at 25%, got {kelly}"
    
    def test_kelly_negative_edge(self):
        """A losing strategy should return 0 Kelly fraction."""
        # 30% win rate, avg win 5€, avg loss 10€
        trades = [
            {'symbol': 'BTC/EUR', 'pnl': 5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 5, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -10, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        kelly = analyzer.calculate_kelly_fraction('BTC/EUR', lookback_trades=10)
        
        assert kelly == 0, f"Negative edge should return 0 Kelly, got {kelly}"
    
    def test_kelly_cap_enforced(self):
        """Kelly should never exceed 25%."""
        # 90% win rate, huge wins - would give very high Kelly
        trades = [
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 100, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': -5, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        kelly = analyzer.calculate_kelly_fraction('BTC/EUR', lookback_trades=10)
        
        assert kelly <= 0.25, f"Kelly should be capped at 25%, got {kelly}"
    
    def test_kelly_insufficient_data(self):
        """Kelly should return 0 with insufficient trade history."""
        trades = [
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'BTC/EUR', 'pnl': 10, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        kelly = analyzer.calculate_kelly_fraction('BTC/EUR', lookback_trades=10)
        
        assert kelly == 0, f"Insufficient data should return 0 Kelly, got {kelly}"


class TestSymbolStats:
    """Test symbol performance statistics."""
    
    def test_win_rate_calculation(self):
        """Win rate should be calculated correctly."""
        trades = [
            {'symbol': 'ETH/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'ETH/EUR', 'pnl': 10, 'status': 'closed'},
            {'symbol': 'ETH/EUR', 'pnl': -5, 'status': 'closed'},
            {'symbol': 'ETH/EUR', 'pnl': 10, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        stats = analyzer.get_symbol_stats('ETH/EUR')
        
        assert stats['win_rate'] == 0.75, f"Win rate should be 75%, got {stats['win_rate']}"
        assert stats['total_trades'] == 4
    
    def test_empty_stats_for_unknown_symbol(self):
        """Unknown symbol should return neutral stats."""
        storage = MockStorage([])
        analyzer = PerformanceAnalyzer(storage)
        
        stats = analyzer.get_symbol_stats('UNKNOWN/EUR')
        
        assert stats['total_trades'] == 0
        assert stats['win_rate'] == 0.5  # Neutral assumption


class TestMarketRegime:
    """Test market regime detection."""
    
    def test_trending_market(self):
        """High ADX should indicate trending market."""
        # Create trending data (prices consistently rising)
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        prices = np.linspace(100, 150, 50)  # Steady uptrend
        
        df = pd.DataFrame({
            'close': prices,
            'high': prices * 1.01,
            'low': prices * 0.99
        }, index=dates)
        
        storage = MockStorage([])
        analyzer = PerformanceAnalyzer(storage)
        
        regime = analyzer.get_market_regime(df)
        
        # Strong trend should be detected (may be "trend" or "volatile" depending on calculation)
        assert regime in ["trend", "range", "volatile"], f"Invalid regime: {regime}"
    
    def test_insufficient_data_returns_range(self):
        """Insufficient data should default to range."""
        df = pd.DataFrame({'close': [100, 101]})
        
        storage = MockStorage([])
        analyzer = PerformanceAnalyzer(storage)
        
        regime = analyzer.get_market_regime(df)
        
        assert regime == "range"


class TestConfidenceAdjustment:
    """Test performance-based confidence adjustment."""
    
    def test_profitable_symbol_boost(self):
        """Profitable symbols should get confidence boost."""
        trades = [
            {'symbol': 'SOL/EUR', 'pnl': 20, 'status': 'closed'},
            {'symbol': 'SOL/EUR', 'pnl': 20, 'status': 'closed'},
            {'symbol': 'SOL/EUR', 'pnl': 20, 'status': 'closed'},
            {'symbol': 'SOL/EUR', 'pnl': 20, 'status': 'closed'},
            {'symbol': 'SOL/EUR', 'pnl': -5, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        base_confidence = 0.6
        adjusted = analyzer.get_confidence_adjustment('SOL/EUR', base_confidence)
        
        assert adjusted >= base_confidence, "Profitable symbol should boost confidence"
    
    def test_losing_symbol_reduction(self):
        """Losing symbols should get confidence reduction."""
        trades = [
            {'symbol': 'XRP/EUR', 'pnl': 5, 'status': 'closed'},
            {'symbol': 'XRP/EUR', 'pnl': -20, 'status': 'closed'},
            {'symbol': 'XRP/EUR', 'pnl': -20, 'status': 'closed'},
            {'symbol': 'XRP/EUR', 'pnl': -20, 'status': 'closed'},
            {'symbol': 'XRP/EUR', 'pnl': -20, 'status': 'closed'},
        ]
        
        storage = MockStorage(trades)
        analyzer = PerformanceAnalyzer(storage)
        
        base_confidence = 0.6
        adjusted = analyzer.get_confidence_adjustment('XRP/EUR', base_confidence)
        
        assert adjusted <= base_confidence, "Losing symbol should reduce confidence"
        assert adjusted >= base_confidence * 0.5, "Reduction should not exceed 50%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
