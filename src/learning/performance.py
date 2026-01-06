"""
Performance Analyzer for Adaptive Trading.

Implements Kelly Criterion position sizing and market regime detection
to enable intelligent, self-improving trading decisions.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple
from loguru import logger
from src.data.storage import DataStorage
from src.config.settings import settings


class PerformanceAnalyzer:
    """
    Analyzes trading performance per symbol and calculates optimal position sizes.
    
    Core features:
    - Per-symbol win rate and average win/loss tracking
    - Kelly Criterion calculation for optimal position sizing
    - Market regime detection (trend/range/volatile)
    """
    
    def __init__(self, storage: DataStorage):
        """Initialize with storage for trade history access."""
        self.storage = storage
        self._cache: Dict[str, dict] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache
    
    def get_symbol_stats(self, symbol: str, lookback_trades: int = 50) -> dict:
        """
        Calculate performance statistics for a specific symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/EUR')
            lookback_trades: Number of recent trades to analyze
            
        Returns:
            dict with keys: win_rate, avg_win, avg_loss, total_trades, profit_factor
        """
        try:
            # Get closed trades from storage
            all_trades = self.storage.get_trades(status='closed')
            
            if all_trades.empty:
                return self._empty_stats()
            
            # Filter by symbol
            symbol_trades = all_trades[all_trades['symbol'] == symbol].head(lookback_trades)
            
            if symbol_trades.empty:
                return self._empty_stats()
            
            # Calculate stats
            wins = symbol_trades[symbol_trades['pnl'] > 0]
            losses = symbol_trades[symbol_trades['pnl'] <= 0]
            
            total = len(symbol_trades)
            win_count = len(wins)
            loss_count = len(losses)
            
            win_rate = win_count / total if total > 0 else 0
            avg_win = wins['pnl'].mean() if not wins.empty else 0
            avg_loss = abs(losses['pnl'].mean()) if not losses.empty else 0
            
            gross_profit = wins['pnl'].sum() if not wins.empty else 0
            gross_loss = abs(losses['pnl'].sum()) if not losses.empty else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
            
            return {
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_trades': total,
                'profit_factor': profit_factor,
                'win_count': win_count,
                'loss_count': loss_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating stats for {symbol}: {e}")
            return self._empty_stats()
    
    def _empty_stats(self) -> dict:
        """Return empty stats when no data available."""
        return {
            'win_rate': 0.5,  # Neutral assumption
            'avg_win': 0,
            'avg_loss': 0,
            'total_trades': 0,
            'profit_factor': 0,
            'win_count': 0,
            'loss_count': 0
        }
    
    def calculate_kelly_fraction(self, symbol: str, lookback_trades: int = 50) -> float:
        """
        Calculate optimal Kelly Criterion betting fraction for a symbol.
        
        Kelly Formula: f* = (p * W - q * L) / W
        Where:
            p = probability of winning (win rate)
            q = probability of losing (1 - p)
            W = average win amount
            L = average loss amount (absolute)
        
        Returns:
            Half-Kelly fraction capped at settings.KELLY_FRACTION_CAP (default 25%)
            Returns 0 if insufficient data or negative expectancy
        """
        stats = self.get_symbol_stats(symbol, lookback_trades)
        
        # Need minimum trades for reliable estimate
        min_trades = 10
        if stats['total_trades'] < min_trades:
            logger.debug(f"Kelly {symbol}: Insufficient trades ({stats['total_trades']} < {min_trades})")
            return 0.0
        
        p = stats['win_rate']
        q = 1 - p
        W = stats['avg_win']
        L = stats['avg_loss']
        
        # Can't calculate without wins/losses
        if W <= 0 or L <= 0:
            logger.debug(f"Kelly {symbol}: Invalid W={W:.2f}, L={L:.2f}")
            return 0.0
        
        # Kelly formula: f* = (p*W - q*L) / W
        # Simplified: f* = p - q*(L/W)
        # Or equivalently: f* = (p*W - (1-p)*L) / W
        
        numerator = (p * W) - (q * L)
        if numerator <= 0:
            # Negative expectancy - don't bet
            logger.debug(f"Kelly {symbol}: Negative edge ({numerator:.4f})")
            return 0.0
        
        kelly_full = numerator / W
        
        # Apply Half-Kelly for safety (standard practice)
        kelly_half = kelly_full * 0.5
        
        # Cap at maximum allowed fraction
        kelly_cap = getattr(settings, 'KELLY_FRACTION_CAP', 0.25)
        kelly_final = min(kelly_half, kelly_cap)
        
        logger.info(f"Kelly {symbol}: rate={p:.1%}, W={W:.2f}, L={L:.2f}, "
                   f"full={kelly_full:.2%}, half={kelly_half:.2%}, final={kelly_final:.2%}")
        
        return kelly_final
    
    def get_market_regime(self, df: pd.DataFrame) -> str:
        """
        Detect market regime using ADX and Bollinger Bands.
        
        Regimes:
        - "trend": ADX > 25, clear directional movement
        - "range": ADX < 20, price bouncing between levels
        - "volatile": High ATR relative to price, unstable conditions
        
        Args:
            df: OHLCV DataFrame with 'close', 'high', 'low' columns
            
        Returns:
            One of: "trend", "range", "volatile"
        """
        if df is None or len(df) < 20:
            return "range"  # Default to range if insufficient data
        
        try:
            # Ensure we have required columns
            if 'close' not in df.columns:
                return "range"
            
            close = df['close'].values
            high = df['high'].values if 'high' in df.columns else close
            low = df['low'].values if 'low' in df.columns else close
            
            # Calculate ADX (simplified)
            adx = self._calculate_adx(high, low, close, period=14)
            
            # Calculate ATR percentage
            atr = self._calculate_atr(high, low, close, period=14)
            atr_percent = (atr / close[-1]) * 100 if close[-1] > 0 else 0
            
            # Determine regime
            adx_threshold = getattr(settings, 'ADX_TREND_THRESHOLD', 25.0)
            
            if atr_percent > 4.0:  # Very high volatility
                return "volatile"
            elif adx > adx_threshold:
                return "trend"
            else:
                return "range"
                
        except Exception as e:
            logger.warning(f"Regime detection error: {e}")
            return "range"
    
    def _calculate_adx(self, high: np.ndarray, low: np.ndarray, 
                       close: np.ndarray, period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)."""
        if len(high) < period + 1:
            return 20.0  # Default neutral value
        
        try:
            # True Range
            tr = np.maximum(high[1:] - low[1:],
                           np.maximum(abs(high[1:] - close[:-1]),
                                     abs(low[1:] - close[:-1])))
            
            # +DM and -DM
            up_move = high[1:] - high[:-1]
            down_move = low[:-1] - low[1:]
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            # Smoothed averages (simple moving average for simplicity)
            atr = np.mean(tr[-period:])
            plus_di = 100 * np.mean(plus_dm[-period:]) / atr if atr > 0 else 0
            minus_di = 100 * np.mean(minus_dm[-period:]) / atr if atr > 0 else 0
            
            # DX and ADX
            di_sum = plus_di + minus_di
            dx = 100 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0
            
            return dx  # Simplified: return DX as proxy for ADX
            
        except Exception:
            return 20.0
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray,
                       close: np.ndarray, period: int = 14) -> float:
        """Calculate ATR (Average True Range)."""
        if len(high) < 2:
            return 0.0
        
        try:
            tr = np.maximum(high[1:] - low[1:],
                           np.maximum(abs(high[1:] - close[:-1]),
                                     abs(low[1:] - close[:-1])))
            return np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
        except Exception:
            return 0.0
    
    def get_all_symbol_performance(self) -> Dict[str, dict]:
        """
        Get performance summary for all traded symbols.
        Useful for dashboard display.
        
        Returns:
            Dict mapping symbol -> stats dict
        """
        # Check cache
        now = datetime.now()
        if (self._cache_time and 
            (now - self._cache_time).total_seconds() < self._cache_ttl_seconds):
            return self._cache
        
        # Build fresh cache
        performance = {}
        for symbol in settings.SYMBOLS:
            stats = self.get_symbol_stats(symbol)
            kelly = self.calculate_kelly_fraction(symbol)
            performance[symbol] = {
                **stats,
                'kelly_fraction': kelly
            }
        
        self._cache = performance
        self._cache_time = now
        
        return performance
    
    def get_confidence_adjustment(self, symbol: str, base_confidence: float) -> float:
        """
        Adjust signal confidence based on historical performance.
        
        Symbols with higher profit factors get boosted confidence,
        losing symbols get reduced confidence (but never below 50% of original).
        
        Args:
            symbol: Trading pair
            base_confidence: Original signal confidence (0-1)
            
        Returns:
            Adjusted confidence (0-1)
        """
        stats = self.get_symbol_stats(symbol)
        
        if stats['total_trades'] < 5:
            # Not enough data to adjust
            return base_confidence
        
        # Profit factor adjustment
        pf = stats['profit_factor']
        
        if pf >= 2.0:
            # Very profitable - boost up to 20%
            multiplier = 1.2
        elif pf >= 1.5:
            # Profitable - boost 10%
            multiplier = 1.1
        elif pf >= 1.0:
            # Break-even - no change
            multiplier = 1.0
        elif pf >= 0.5:
            # Losing - reduce 10%
            multiplier = 0.9
        else:
            # Heavy losses - reduce 20%
            multiplier = 0.8
        
        adjusted = base_confidence * multiplier
        
        # Clamp between 50% of original and 1.0
        return max(min(adjusted, 1.0), base_confidence * 0.5)
