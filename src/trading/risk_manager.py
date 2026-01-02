"""
Risk Manager for Trading Operations.

Implements position sizing, stop-loss, take-profit, and 
portfolio-level risk controls.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
import pandas as pd
from src.config.settings import settings


@dataclass
class RiskConfig:
    """Risk management configuration."""
    # Position sizing
    max_position_percent: float = 0.15        # Max 15% of capital per position
    min_trade_value: float = 100.0            # Minimum $100 per trade
    risk_per_trade_percent: float = 0.02      # Risk 2% per trade
    
    # Stop-loss / Take-profit
    default_stop_loss: float = 0.025          # 2.5% stop loss
    default_take_profit: float = 0.045        # 4.5% take profit (1.8:1 R:R)
    trailing_stop_percent: float = 0.015      # 1.5% trailing stop
    
    # Trade frequency limits
    max_daily_trades: int = settings.MAX_DAILY_TRADES
    max_trades_per_symbol: int = 2            # Max 2 open trades per symbol
    cooldown_minutes: int = settings.COOLDOWN_MINUTES
    
    # Portfolio limits
    max_open_positions: int = settings.MAX_OPEN_POSITIONS
    max_total_exposure: float = 0.60          # Max 60% of capital exposed
    max_correlated_positions: int = 3         # Max 3 highly correlated
    
    # Emergency controls
    max_daily_loss_percent: float = settings.MAX_DAILY_LOSS
    max_drawdown_percent: float = 0.15        # Pause at -15% drawdown
    
    # Signal thresholds
    min_confidence: float = 0.55              # Minimum signal confidence
    strong_signal_confidence: float = 0.75    # Confidence for larger positions


@dataclass
class TradeRecord:
    """Record of a trade for risk tracking."""
    symbol: str
    side: str
    entry_price: float
    amount: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    
    
@dataclass
class RiskState:
    """Current risk state."""
    daily_pnl: float = 0.0
    daily_trades: int = 0
    last_trade_time: Dict[str, datetime] = field(default_factory=dict)
    open_positions: Dict[str, TradeRecord] = field(default_factory=dict)
    peak_balance: float = 1000.0
    current_drawdown: float = 0.0


class RiskManager:
    """
    Portfolio-level risk management.
    
    Handles position sizing, trade validation, and risk limits.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """Initialize risk manager with config."""
        self.config = config or RiskConfig()
        self.state = RiskState()
        self._daily_reset_time = datetime.now().replace(hour=0, minute=0)
        
    def reset_daily_stats(self):
        """Reset daily statistics at start of new day."""
        now = datetime.now()
        if now.date() > self._daily_reset_time.date():
            logger.info("Resetting daily risk stats")
            self.state.daily_pnl = 0.0
            self.state.daily_trades = 0
            self._daily_reset_time = now
    
    def can_trade(self, symbol: str, balance: float) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk limits.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        self.reset_daily_stats()
        
        # Check daily loss limit
        if self.state.daily_pnl < -(balance * self.config.max_daily_loss_percent):
            return False, f"Daily loss limit reached ({self.state.daily_pnl:.2f})"
        
        # Check daily trade limit
        if self.state.daily_trades >= self.config.max_daily_trades:
            return False, f"Max daily trades reached ({self.config.max_daily_trades})"
        
        # Check max open positions
        if len(self.state.open_positions) >= self.config.max_open_positions:
            return False, f"Max open positions reached ({self.config.max_open_positions})"
        
        # Check position for this symbol
        symbol_positions = sum(1 for s in self.state.open_positions if s == symbol)
        if symbol_positions >= self.config.max_trades_per_symbol:
            return False, f"Max positions for {symbol} reached"
        
        # Check cooldown
        if symbol in self.state.last_trade_time:
            elapsed = (datetime.now() - self.state.last_trade_time[symbol]).total_seconds()
            if elapsed < self.config.cooldown_minutes * 60:
                remaining = self.config.cooldown_minutes - (elapsed / 60)
                return False, f"Cooldown active for {symbol} ({remaining:.1f}min remaining)"
        
        # Check drawdown
        if self.state.current_drawdown > self.config.max_drawdown_percent:
            return False, f"Max drawdown reached ({self.state.current_drawdown*100:.1f}%)"
        
        # Check total exposure
        total_exposure = sum(
            pos.entry_price * pos.amount 
            for pos in self.state.open_positions.values()
        )
        if total_exposure > balance * self.config.max_total_exposure:
            return False, f"Max exposure reached ({total_exposure:.2f})"
        
        return True, "Trade allowed"
    
    def calculate_position_size(
        self, 
        balance: float, 
        price: float, 
        confidence: float,
        volatility_factor: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        Calculate position size with risk management.
        
        Args:
            balance: Available balance
            price: Asset price
            confidence: Signal confidence 0-1
            volatility_factor: Multiplier for high volatility (reduce size)
            
        Returns:
            Tuple of (position_size, stop_loss_price, take_profit_price)
        """
        if balance < self.config.min_trade_value:
            return 0, 0, 0
            
        # Base position from risk per trade
        risk_amount = balance * self.config.risk_per_trade_percent
        position_value = risk_amount / self.config.default_stop_loss
        
        # Adjust for confidence (higher confidence = larger position)
        if confidence >= self.config.strong_signal_confidence:
            confidence_multiplier = 1.2
        elif confidence >= self.config.min_confidence:
            confidence_multiplier = 0.8 + (confidence - self.config.min_confidence) * 2
        else:
            return 0, 0, 0  # Below minimum confidence
        
        position_value *= confidence_multiplier
        
        # Adjust for volatility
        position_value *= (1 / max(volatility_factor, 0.5))
        
        # Apply max position constraint
        max_value = balance * self.config.max_position_percent
        position_value = min(position_value, max_value)
        
        # Check minimum
        if position_value < self.config.min_trade_value:
            return 0, 0, 0
            
        # Calculate size in asset units
        position_size = position_value / price
        
        # Calculate stop loss and take profit prices
        stop_loss = price * (1 - self.config.default_stop_loss)
        take_profit = price * (1 + self.config.default_take_profit)
        
        return position_size, stop_loss, take_profit
    
    def should_close_position(
        self, 
        trade_id: str,
        current_price: float,
        side: str
    ) -> Tuple[bool, str]:
        """
        Check if position should be closed based on SL/TP.
        
        Returns:
            Tuple of (should_close, reason)
        """
        if trade_id not in self.state.open_positions:
            return False, "Position not found"
            
        pos = self.state.open_positions[trade_id]
        
        if side == 'buy':
            # Long position
            if current_price <= pos.stop_loss:
                return True, f"Stop loss hit at {current_price:.2f}"
            if current_price >= pos.take_profit:
                return True, f"Take profit hit at {current_price:.2f}"
        else:
            # Short position (inverted logic)
            stop_loss_short = pos.entry_price * (1 + self.config.default_stop_loss)
            take_profit_short = pos.entry_price * (1 - self.config.default_take_profit)
            
            if current_price >= stop_loss_short:
                return True, f"Stop loss hit at {current_price:.2f}"
            if current_price <= take_profit_short:
                return True, f"Take profit hit at {current_price:.2f}"
        
        return False, "Position OK"
    
    def register_trade(
        self, 
        trade_id: str,
        symbol: str, 
        side: str,
        entry_price: float, 
        amount: float,
        stop_loss: float,
        take_profit: float
    ):
        """Register a new trade in risk tracking."""
        self.state.open_positions[trade_id] = TradeRecord(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            amount=amount,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.state.last_trade_time[symbol] = datetime.now()
        self.state.daily_trades += 1
        
        logger.info(f"Registered trade {trade_id}: {side} {amount} {symbol} @ {entry_price}")
    
    def close_trade(self, trade_id: str, pnl: float):
        """Close a trade and update stats."""
        if trade_id in self.state.open_positions:
            del self.state.open_positions[trade_id]
            
        self.state.daily_pnl += pnl
        logger.info(f"Closed trade {trade_id}: PnL = {pnl:+.2f}")
    
    def update_balance(self, balance: float):
        """Update balance and calculate drawdown."""
        if balance > self.state.peak_balance:
            self.state.peak_balance = balance
            
        self.state.current_drawdown = (
            (self.state.peak_balance - balance) / self.state.peak_balance
            if self.state.peak_balance > 0 else 0
        )
    
    def get_risk_summary(self) -> Dict:
        """Get summary of current risk state."""
        return {
            "daily_pnl": self.state.daily_pnl,
            "daily_trades": self.state.daily_trades,
            "open_positions": len(self.state.open_positions),
            "current_drawdown": f"{self.state.current_drawdown*100:.1f}%",
            "peak_balance": self.state.peak_balance,
            "can_trade": self.state.daily_trades < self.config.max_daily_trades
        }


# Correlation matrix for crypto pairs (simplified)
CRYPTO_CORRELATIONS = {
    ("BTC/USDT", "ETH/USDT"): 0.85,
    ("BTC/USDT", "SOL/USDT"): 0.75,
    ("ETH/USDT", "SOL/USDT"): 0.80,
    ("BTC/USDT", "BNB/USDT"): 0.70,
    ("BTC/USDT", "XRP/USDT"): 0.65,
    ("BTC/USDT", "ADA/USDT"): 0.60,
    ("BTC/USDT", "DOGE/USDT"): 0.55,
}


def get_correlation(symbol1: str, symbol2: str) -> float:
    """Get correlation between two symbols."""
    if symbol1 == symbol2:
        return 1.0
    
    key = (symbol1, symbol2) if symbol1 < symbol2 else (symbol2, symbol1)
    return CRYPTO_CORRELATIONS.get(key, 0.5)
