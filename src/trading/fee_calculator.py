"""
Fee Calculator for Kraken Margin Trading.

Calculates all applicable fees for margin trading positions:
- Entry fees (taker fee + margin opening fee)
- Exit fees (taker fee)
- Rollover fees (accumulated every 4 hours)
"""
from datetime import datetime
from typing import Dict
from src.config.settings import settings


class FeeCalculator:
    """
    Centralized fee calculation for margin trading.
    
    Kraken margin trading fees:
    - Opening fee: 0.02% of position value
    - Rollover fee: 0.02% every 4 hours
    - Trading fee: 0.1% (taker) on entry and exit
    """
    
    def __init__(self):
        """Initialize with settings."""
        self.taker_fee = settings.TAKER_FEE
        self.maker_fee = settings.MAKER_FEE
        self.margin_opening_fee = settings.MARGIN_OPENING_FEE
        self.margin_rollover_fee = settings.MARGIN_ROLLOVER_FEE
        self.rollover_interval_hours = settings.ROLLOVER_INTERVAL_HOURS
        self.slippage = getattr(settings, 'SLIPPAGE_PERCENT', 0.0005)  # 0.05% default
    
    def calculate_slippage(self, trade_value: float) -> float:
        """
        Simulate market slippage for paper trading realism.
        
        Args:
            trade_value: Value of the trade
            
        Returns:
            Estimated slippage cost
        """
        return trade_value * self.slippage
    
    def calculate_entry_fees(self, trade_value: float, is_margin: bool = True) -> Dict[str, float]:
        """
        Calculate all fees for opening a position.
        
        Args:
            trade_value: Total value of the trade (price * amount)
            is_margin: Whether this is a margin trade (default True)
            
        Returns:
            Dict with 'trading_fee', 'margin_fee', and 'total' keys
        """
        # Trading fee (taker for market orders)
        trading_fee = trade_value * self.taker_fee
        
        # Margin opening fee (only for margin trades)
        margin_fee = trade_value * self.margin_opening_fee if is_margin else 0.0
        
        total = trading_fee + margin_fee
        
        return {
            'trading_fee': trading_fee,
            'margin_fee': margin_fee,
            'slippage': self.calculate_slippage(trade_value),
            'total': total + self.calculate_slippage(trade_value)
        }
    
    def calculate_exit_fees(self, trade_value: float) -> float:
        """
        Calculate fees for closing a position.
        
        Args:
            trade_value: Total value of the trade at exit (exit_price * amount)
            
        Returns:
            Exit fee amount (taker fee)
        """
        return trade_value * self.taker_fee
    
    def calculate_rollover_fees(self, trade_value: float, entry_time: datetime, 
                                 exit_time: datetime = None) -> float:
        """
        Calculate accumulated rollover fees for a position.
        
        Kraken charges rollover fee every 4 hours that a position is open.
        
        Args:
            trade_value: Position value (entry_price * amount)
            entry_time: When the position was opened
            exit_time: When the position was closed (default: now)
            
        Returns:
            Total rollover fees accumulated
        """
        if exit_time is None:
            exit_time = datetime.now()
        
        # Handle timezone-aware datetimes
        if hasattr(entry_time, 'replace'):
            entry_time = entry_time.replace(tzinfo=None) if entry_time.tzinfo else entry_time
        if hasattr(exit_time, 'replace'):
            exit_time = exit_time.replace(tzinfo=None) if exit_time.tzinfo else exit_time
        
        # Calculate hours open
        duration = exit_time - entry_time
        hours_open = duration.total_seconds() / 3600
        
        # Calculate number of rollover periods (charged every 4 hours)
        # First period is free, then charged at each interval
        rollover_periods = int(hours_open / self.rollover_interval_hours)
        
        # Calculate total rollover fee
        rollover_fee = trade_value * self.margin_rollover_fee * rollover_periods
        
        return rollover_fee
    
    def calculate_total_fees(self, entry_fee: float, exit_fee: float, 
                             rollover_fee: float) -> float:
        """
        Calculate total fees for a completed trade.
        
        Args:
            entry_fee: Fee paid on entry
            exit_fee: Fee paid on exit
            rollover_fee: Accumulated rollover fees
            
        Returns:
            Total fees for the trade
        """
        return entry_fee + exit_fee + rollover_fee
    
    def calculate_all_fees_for_trade(self, entry_price: float, exit_price: float,
                                      amount: float, entry_time: datetime,
                                      exit_time: datetime = None,
                                      is_margin: bool = True) -> Dict[str, float]:
        """
        Calculate all fees for a complete trade lifecycle.
        
        Args:
            entry_price: Price at entry
            exit_price: Price at exit
            amount: Position size
            entry_time: When position was opened
            exit_time: When position was closed (default: now)
            is_margin: Whether this is a margin trade
            
        Returns:
            Dict with all fee components and totals:
            - entry_fee: Total entry fees (trading + margin opening)
            - exit_fee: Exit trading fee
            - rollover_fee: Accumulated rollover fees
            - total_fees: Sum of all fees
        """
        entry_value = entry_price * amount
        exit_value = exit_price * amount
        
        entry_fees = self.calculate_entry_fees(entry_value, is_margin)
        exit_fee = self.calculate_exit_fees(exit_value)
        rollover_fee = self.calculate_rollover_fees(entry_value, entry_time, exit_time)
        
        total_fees = self.calculate_total_fees(
            entry_fees['total'], 
            exit_fee, 
            rollover_fee
        )
        
        return {
            'entry_fee': entry_fees['total'],
            'entry_trading_fee': entry_fees['trading_fee'],
            'entry_margin_fee': entry_fees['margin_fee'],
            'exit_fee': exit_fee,
            'rollover_fee': rollover_fee,
            'total_fees': total_fees
        }


# Singleton instance for easy access
fee_calculator = FeeCalculator()
