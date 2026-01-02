"""
Optimized Live Trading Bot with ML-Based Strategy.

This bot uses:
- Technical indicator analysis
- ML signal generation  
- Risk management with position sizing
- Stop-loss and take-profit automation
"""
import sys
import os
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pandas as pd
from loguru import logger

from src.data.storage import DataStorage
from src.data.collector import DataCollector
from src.config.settings import settings
from src.features.technical import TechnicalFeatures
from src.ml.signal_generator import SignalGenerator, MLSignal
from src.trading.risk_manager import RiskManager, RiskConfig


# Configure logging - ASCII only for Windows compatibility
logger.remove()
logger.add(
    sys.stdout, 
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    colorize=False
)
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8"
)


class OptimizedTradingBot:
    """
    Production-ready trading bot with ML signals and risk management.
    """
    
    def __init__(self):
        """Initialize the trading bot with all components."""
        self.storage = DataStorage()
        self.collector = DataCollector()
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager(RiskConfig(
            max_daily_trades=settings.MAX_DAILY_TRADES,
            max_open_positions=settings.MAX_OPEN_POSITIONS,
            max_daily_loss_percent=settings.MAX_DAILY_LOSS,
            cooldown_minutes=settings.COOLDOWN_MINUTES
        ))
        
        # Check if we have API keys for live trading
        if settings.ACTIVE_EXCHANGE == "binance":
            self.is_live = (settings.BINANCE_API_KEY is not None and settings.BINANCE_SECRET_KEY is not None)
            # Create symbols matching exchange format
            self.symbols = settings.SYMBOLS
        elif settings.ACTIVE_EXCHANGE == "bybit":
            self.is_live = (settings.BYBIT_API_KEY is not None and settings.BYBIT_SECRET_KEY is not None)
            # Bybit often uses same format 'BTC/USDT' for spot, but good to ensure
            self.symbols = settings.SYMBOLS

        
        # Paper trading balance
        self.total_balance = 1000.0
        self.free_balance = 1000.0
        self.used_balance = 0.0
        
        # Load previous balance if exists
        latest = self.storage.get_latest_balance()
        if latest["total"] > 0:
            self.total_balance = latest["total"]
            self.free_balance = latest["free"]
            self.used_balance = latest["used"]
            
        logger.info(f"Bot initialized on {settings.ACTIVE_EXCHANGE.upper()} - Mode: {'LIVE' if self.is_live else 'PAPER'}")
        
        # Track open positions for SL/TP monitoring
        self.open_positions: Dict[str, dict] = {}
        
        # Data cache
        self.price_cache: Dict[str, float] = {}
        self.last_analysis: Dict[str, datetime] = {}
        
        # Analysis cooldown (don't analyze too frequently)
        self.analysis_cooldown = timedelta(minutes=5)
        
        logger.info(f"Trading symbols: {self.symbols}")
    
    async def initialize(self):
        """Warm up the bot with historical data."""
        logger.info("[INIT] Initializing bot with historical data...")
        
        # Update balance in DB
        self.storage.update_balance(self.total_balance, self.free_balance, self.used_balance)
        
        # Load open positions from DB
        open_trades = self.storage.get_trades(status="open")
        for _, trade in open_trades.iterrows():
            self.open_positions[trade['id']] = {
                'symbol': trade['symbol'],
                'side': trade['side'],
                'entry_price': trade['entry_price'],
                'amount': trade['amount'],
                'entry_time': trade['entry_time'],
            }
            self.risk_manager.register_trade(
                trade['id'],
                trade['symbol'],
                trade['side'],
                trade['entry_price'],
                trade['amount'],
                trade['entry_price'] * 0.975,  # 2.5% stop loss
                trade['entry_price'] * 1.045   # 4.5% take profit
            )
        
        logger.info(f"Loaded {len(self.open_positions)} open positions")
        
        # Fetch initial data for all symbols
        for symbol in self.symbols:
            try:
                df = await self.collector.fetch_ohlcv(symbol, "1h", limit=200)
                if not df.empty:
                    self.storage.save_ohlcv(df, symbol, "binance", "1h")
                    logger.info(f"[OK] Loaded {len(df)} candles for {symbol}")
            except Exception as e:
                logger.error(f"Error loading {symbol}: {e}")
        
        logger.info("Initialization complete")
    
    async def fetch_and_analyze(self, symbol: str) -> Tuple[Optional[float], Optional[MLSignal]]:
        """
        Fetch latest data and generate signal for a symbol.
        
        Returns:
            Tuple of (current_price, signal)
        """
        try:
            # Fetch latest candles
            df = await self.collector.fetch_ohlcv(symbol, "1h", limit=100)
            
            if df.empty:
                return None, None
            
            # Save to storage
            self.storage.save_ohlcv(df, symbol, "binance", "1h")
            
            current_price = df.iloc[-1]['close']
            self.price_cache[symbol] = current_price
            
            # Check if we should analyze (cooldown)
            now = datetime.now()
            if symbol in self.last_analysis:
                if now - self.last_analysis[symbol] < self.analysis_cooldown:
                    return current_price, None
            
            # Add technical indicators
            df = TechnicalFeatures.add_all_features(df, include_advanced=True)
            
            # Generate signal
            signal = self.signal_generator.generate(df, symbol)
            
            self.last_analysis[symbol] = now
            
            return current_price, signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None, None
    
    async def check_open_positions(self):
        """Check open positions for stop-loss or take-profit."""
        if not self.open_positions:
            return
        
        positions_to_close = []
        
        for trade_id, position in self.open_positions.items():
            symbol = position['symbol']
            current_price = self.price_cache.get(symbol)
            
            if current_price is None:
                continue
            
            entry_price = position['entry_price']
            side = position['side']
            amount = position['amount']
            
            # Calculate P&L
            if side == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            pnl = pnl_pct * (entry_price * amount)
            
            # Check stop-loss (2.5%)
            if pnl_pct <= -0.025:
                positions_to_close.append((trade_id, current_price, "STOP_LOSS", pnl))
                logger.warning(f"[STOP LOSS] {symbol} | PnL: {pnl_pct*100:.2f}%")
            
            # Check take-profit (4.5%)
            elif pnl_pct >= 0.045:
                positions_to_close.append((trade_id, current_price, "TAKE_PROFIT", pnl))
                logger.info(f"[TAKE PROFIT] {symbol} | PnL: {pnl_pct*100:.2f}%")
            
            # Check trailing stop (if profit > 2%, stop at 1.5% profit)
            elif pnl_pct >= 0.02:
                trailing_trigger = 0.015  # Trigger trailing stop at 1.5%
                if pnl_pct < trailing_trigger:
                    positions_to_close.append((trade_id, current_price, "TRAILING_STOP", pnl))
                    logger.info(f"[TRAILING STOP] {symbol} | PnL: {pnl_pct*100:.2f}%")
        
        # Close positions
        for trade_id, exit_price, reason, pnl in positions_to_close:
            await self.close_position(trade_id, exit_price, reason, pnl)
    
    async def close_position(self, trade_id: str, exit_price: float, reason: str, pnl: float):
        """Close a position and update records."""
        if trade_id not in self.open_positions:
            return
        
        position = self.open_positions[trade_id]
        symbol = position['symbol']
        amount = position['amount']
        entry_price = position['entry_price']
        
        # Calculate fee
        fee = exit_price * amount * 0.001  # 0.1% fee
        net_pnl = pnl - fee
        
        # Update trade record
        trade_update = {
            "id": trade_id,
            "status": "closed",
            "exit_price": exit_price,
            "exit_time": pd.Timestamp.now(),
            "pnl": net_pnl
        }
        self.storage.save_trade(trade_update)
        
        # Update balance
        self.free_balance += (amount * entry_price) + net_pnl
        self.used_balance -= (amount * entry_price)
        self.total_balance = self.free_balance + self.used_balance
        self.storage.update_balance(self.total_balance, self.free_balance, self.used_balance)
        
        # Update risk manager
        self.risk_manager.close_trade(trade_id, net_pnl)
        self.risk_manager.update_balance(self.total_balance)
        
        # Remove from tracking
        del self.open_positions[trade_id]
        
        status = "[WIN]" if net_pnl >= 0 else "[LOSS]"
        logger.info(
            f"{status} CLOSED {position['side'].upper()} {symbol} | "
            f"Entry: ${entry_price:,.2f} -> Exit: ${exit_price:,.2f} | "
            f"PnL: ${net_pnl:+,.2f} ({reason})"
        )
    
    async def execute_signal(self, symbol: str, signal: MLSignal, current_price: float):
        """Execute a trade based on signal if conditions are met."""
        if not signal.is_actionable:
            return
        
        # Check if we can trade
        can_trade, reason = self.risk_manager.can_trade(symbol, self.free_balance)
        if not can_trade:
            logger.debug(f"[{symbol}] Trade blocked: {reason}")
            return
        
        # Calculate position size
        position_size, stop_loss, take_profit = self.risk_manager.calculate_position_size(
            balance=self.free_balance,
            price=current_price,
            confidence=signal.confidence
        )
        
        if position_size <= 0:
            logger.debug(f"[{symbol}] Position size too small")
            return
        
        # Calculate trade value
        trade_value = position_size * current_price
        fee = trade_value * 0.001  # 0.1% fee
        
        # Create trade record
        trade_id = str(uuid.uuid4())[:8]
        side = signal.action.lower()
        
        trade_data = {
            "id": trade_id,
            "symbol": symbol,
            "side": side,
            "type": "market",
            "status": "open",
            "entry_price": current_price,
            "amount": position_size,
            "entry_time": pd.Timestamp.now(),
            "fee": fee
        }
        
        # Save trade
        self.storage.save_trade(trade_data)
        
        # Update balance
        self.free_balance -= trade_value
        self.used_balance += trade_value
        self.storage.update_balance(self.total_balance, self.free_balance, self.used_balance)
        
        # Register with risk manager
        self.risk_manager.register_trade(
            trade_id, symbol, side, current_price, position_size, stop_loss, take_profit
        )
        
        # Track locally
        self.open_positions[trade_id] = {
            'symbol': symbol,
            'side': side,
            'entry_price': current_price,
            'amount': position_size,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
        }
        
        logger.info(
            f"[OPEN] {side.upper()} {symbol} | "
            f"Size: {position_size:.6f} @ ${current_price:,.2f} | "
            f"Value: ${trade_value:,.2f} | Confidence: {signal.confidence:.0%}"
        )
        logger.info(f"   Reasons: {', '.join(signal.reasons[:3])}")
        logger.info(f"   SL: ${stop_loss:,.2f} | TP: ${take_profit:,.2f}")
    
    async def run_cycle(self):
        """Run one trading cycle across all symbols."""
        logger.debug("Starting trading cycle...")
        
        # Check risk limits first
        self.risk_manager.reset_daily_stats()
        risk_summary = self.risk_manager.get_risk_summary()
        
        if not risk_summary['can_trade']:
            logger.warning("Trading paused due to risk limits")
            return
        
        # Check open positions for SL/TP
        await self.check_open_positions()
        
        # Analyze each symbol
        for symbol in self.symbols:
            try:
                price, signal = await self.fetch_and_analyze(symbol)
                
                if price is None:
                    continue
                
                # Log current state
                logger.debug(f"[{symbol}] Price: ${price:,.2f}")
                
                # Execute if we have a strong signal
                if signal and signal.is_actionable:
                    await self.execute_signal(symbol, signal, price)
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        
        # Summary log
        logger.info(
            f"[BALANCE] Total: ${self.total_balance:,.2f} | "
            f"Free: ${self.free_balance:,.2f} | "
            f"Positions: {len(self.open_positions)} | "
            f"Daily Trades: {risk_summary['daily_trades']}"
        )
    
    async def run(self):
        """Main bot loop."""
        await self.initialize()
        
        print("\n" + "="*70)
        print("      ANTIGRAVITY TRADING BOT - OPTIMIZED ML STRATEGY")
        print(f"      MODE: {'LIVE TRADING' if self.is_live else 'PAPER TRADING (REAL PRICES)'}")
        print(f"      SYMBOLS: {len(self.symbols)} | INITIAL BALANCE: ${self.total_balance:,.2f}")
        print("="*70 + "\n")
        
        # Trading loop
        cycle_interval = 60  # 60 seconds between cycles (swing trading)
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"=== Cycle {iteration} @ {datetime.now().strftime('%H:%M:%S')} ===")
                
                await self.run_cycle()
                
                # Wait before next cycle
                logger.debug(f"Next cycle in {cycle_interval}s...")
                await asyncio.sleep(cycle_interval)
                
        except asyncio.CancelledError:
            logger.info("Bot execution cancelled")
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        finally:
            logger.info("Saving state and closing connections...")
            await self.collector.close()
            logger.info("[OK] Bot stopped correctly")


async def main():
    """Entry point."""
    bot = OptimizedTradingBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
