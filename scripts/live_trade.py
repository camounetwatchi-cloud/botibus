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
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

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
        
        # Check if we have API keys for live trading
        exchange_id = settings.ACTIVE_EXCHANGE
        if exchange_id == "binance":
            self.is_live = (settings.BINANCE_API_KEY is not None and settings.BINANCE_SECRET_KEY is not None)
        elif exchange_id == "bybit":
            self.is_live = (settings.BYBIT_API_KEY is not None and settings.BYBIT_SECRET_KEY is not None)
        elif exchange_id == "kraken":
            self.is_live = (settings.KRAKEN_API_KEY is not None and settings.KRAKEN_SECRET_KEY is not None)
        
        # Override with setting
        if settings.PAPER_TRADING:
            self.is_live = False
        
        # Use appropriate max positions based on mode
        max_positions = settings.MAX_OPEN_POSITIONS if not self.is_live else settings.MAX_OPEN_POSITIONS_LIVE
        
        self.risk_manager = RiskManager(RiskConfig(
            max_daily_trades=settings.MAX_DAILY_TRADES,
            max_open_positions=max_positions,
            max_daily_loss_percent=settings.MAX_DAILY_LOSS,
            cooldown_minutes=settings.COOLDOWN_MINUTES
        ))
            
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
        logger.info(f"Max positions: {max_positions} | Min trade: ${settings.MIN_TRADE_VALUE}")
        
        # Track open positions for SL/TP monitoring
        self.open_positions: Dict[str, dict] = {}
        
        # Track peak prices for trailing stops
        self.position_peaks: Dict[str, float] = {}
        
        # Data cache
        self.price_cache: Dict[str, float] = {}
        self.atr_cache: Dict[str, float] = {}  # Cache ATR for dynamic TP
        self.last_analysis: Dict[str, datetime] = {}
        
        # Analysis cooldown (AGGRESSIVE: reduced for more frequent analysis)
        self.analysis_cooldown = timedelta(seconds=10)
        
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
        
        # Load cooldown state from database (persist across restarts)
        cooldowns = self.storage.get_cooldowns()
        for symbol, last_time in cooldowns.items():
            self.risk_manager.state.last_trade_time[symbol] = last_time
        logger.info(f"Loaded {len(cooldowns)} cooldown states from DB")
        
        # Clear expired cooldowns
        self.storage.clear_expired_cooldowns(settings.COOLDOWN_MINUTES)
        
        # PARALLEL fetch for faster initialization
        async def fetch_symbol(sym):
            try:
                df = await self.collector.fetch_ohlcv(sym, "1h", limit=100)
                if not df.empty:
                    self.storage.save_ohlcv(df, sym, settings.ACTIVE_EXCHANGE, "1h")
                    return (sym, len(df), None)
                return (sym, 0, None)
            except Exception as e:
                return (sym, 0, str(e))
        
        results = await asyncio.gather(*[fetch_symbol(s) for s in self.symbols])
        for sym, count, err in results:
            if err:
                logger.error(f"Error loading {sym}: {err}")
            elif count > 0:
                logger.info(f"[OK] Loaded {count} candles for {sym}")
        
        logger.info("Initialization complete")
    
    async def fetch_and_analyze(self, symbol: str) -> Tuple[Optional[float], Optional[MLSignal]]:
        """
        Fetch latest data and generate signal for a symbol.
        
        Returns:
            Tuple of (current_price, signal)
        """
        try:
            # Fetch latest candles
            df = await self.collector.fetch_ohlcv(symbol, "1h", limit=50)
            
            if df.empty:
                return None, None
            
            # NOTE: OHLCV saved only at initialization for speed
            
            current_price = df.iloc[-1]['close']
            self.price_cache[symbol] = current_price
            
            # Get ATR for dynamic TP calculation
            atr = df.iloc[-1].get('ATRr_14', 0) if 'ATRr_14' in df.columns else 0
            if atr == 0 and len(df) >= 14:
                # Calculate ATR manually if not present
                high_low = df['high'] - df['low']
                high_close = abs(df['high'] - df['close'].shift())
                low_close = abs(df['low'] - df['close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.tail(14).mean()
            self.atr_cache[symbol] = atr
            
            # Check if we should analyze (cooldown)
            now = datetime.now()
            if symbol in self.last_analysis:
                if now - self.last_analysis[symbol] < self.analysis_cooldown:
                    return current_price, None
            
            # Add technical indicators
            df = TechnicalFeatures.add_all_features(df, include_advanced=False)
            
            # Generate signal
            signal = self.signal_generator.generate(df, symbol)
            
            # DEBUG: Log calculated scores for visibility
            if signal:
                logger.debug(
                    f"[{symbol}] Scores -> Tech: {signal.technical_score:.2f}, "
                    f"ML: {signal.ml_score:.2f}, Vol: {signal.volume_score:.2f} "
                    f"= Conf: {signal.confidence:.2f} ({signal.action})"
                )
            
            # Attach ATR to signal for dynamic TP
            if signal:
                signal.atr = atr
            
            self.last_analysis[symbol] = now
            
            return current_price, signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None, None
    
    async def check_open_positions(self):
        """Check open positions for stop-loss, take-profit, or trailing stop."""
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
            
            # Update peak price for trailing stop
            if trade_id not in self.position_peaks:
                self.position_peaks[trade_id] = current_price
            elif side == 'buy' and current_price > self.position_peaks[trade_id]:
                self.position_peaks[trade_id] = current_price
            elif side == 'sell' and current_price < self.position_peaks[trade_id]:
                self.position_peaks[trade_id] = current_price
            
            peak_price = self.position_peaks[trade_id]
            
            # Calculate P&L
            if side == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            pnl = pnl_pct * (entry_price * amount)
            
            # Check TRAILING STOP first (higher priority)
            should_trail, trail_price, trail_reason = self.risk_manager.calculate_trailing_stop(
                entry_price, current_price, peak_price, side
            )
            if should_trail:
                positions_to_close.append((trade_id, current_price, "TRAILING_STOP", pnl))
                logger.info(f"[TRAILING STOP] {symbol} | Peak: ${peak_price:.2f} | PnL: {pnl_pct*100:.2f}%")
                continue
            
            # Check stop-loss (2.5%)
            if pnl_pct <= -settings.DEFAULT_STOP_LOSS:
                positions_to_close.append((trade_id, current_price, "STOP_LOSS", pnl))
                logger.warning(f"[STOP LOSS] {symbol} | PnL: {pnl_pct*100:.2f}%")
            
            # Check dynamic take-profit
            atr = self.atr_cache.get(symbol, 0)
            dynamic_tp = self.risk_manager.calculate_dynamic_take_profit(entry_price, atr)
            tp_pct = (dynamic_tp - entry_price) / entry_price
            
            if pnl_pct >= tp_pct:
                positions_to_close.append((trade_id, current_price, "TAKE_PROFIT", pnl))
                logger.info(f"[TAKE PROFIT] {symbol} | Target: {tp_pct*100:.1f}% | PnL: {pnl_pct*100:.2f}%")
        
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
        
        # Clean up peak tracking
        if trade_id in self.position_peaks:
            del self.position_peaks[trade_id]
        
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
        
        # Check if we can trade (use total_balance for exposure check, not free_balance)
        can_trade, reason = self.risk_manager.can_trade(symbol, self.total_balance)
        if not can_trade:
            logger.info(f"[{symbol}] Trade blocked: {reason}")
            return
        
        # Get ATR for dynamic TP calculation
        atr = getattr(signal, 'atr', 0) or self.atr_cache.get(symbol, 0)
        
        # Calculate position size with dynamic TP
        position_size, stop_loss, take_profit = self.risk_manager.calculate_position_size(
            balance=self.free_balance,
            price=current_price,
            confidence=signal.confidence,
            atr=atr
        )
        
        if position_size <= 0:
            logger.info(f"[{symbol}] Position size too small")
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
        
        # Save cooldown to database for persistence across restarts
        self.storage.save_cooldown(symbol, datetime.now())
        
        # Initialize peak price tracking
        self.position_peaks[trade_id] = current_price
        
        # Calculate TP percentage for logging
        tp_pct = ((take_profit - current_price) / current_price) * 100
        
        logger.info(
            f"[OPEN] {side.upper()} {symbol} | "
            f"Size: {position_size:.6f} @ ${current_price:,.2f} | "
            f"Value: ${trade_value:,.2f} | Confidence: {signal.confidence:.0%}"
        )
        logger.info(f"   Reasons: {', '.join(signal.reasons[:3])}")
        logger.info(f"   SL: ${stop_loss:,.2f} (-2.5%) | TP: ${take_profit:,.2f} (+{tp_pct:.1f}%)")
    
    async def run_cycle(self):
        """Run one trading cycle across all symbols with parallel analysis."""
        logger.debug("Starting trading cycle...")
        
        # Check risk limits first
        self.risk_manager.reset_daily_stats()
        risk_summary = self.risk_manager.get_risk_summary()
        
        if not risk_summary['can_trade']:
            logger.warning("Trading paused due to risk limits")
            return
        
        # Check open positions for SL/TP/Trailing
        await self.check_open_positions()
        
        # PARALLEL analysis of all symbols for faster execution
        results = await asyncio.gather(*[
            self.fetch_and_analyze(symbol) 
            for symbol in self.symbols
        ], return_exceptions=True)
        
        # Process results
        signals_found = 0
        successful_symbols = 0
        failed_symbols = []
        
        for symbol, result in zip(self.symbols, results):
            if isinstance(result, Exception):
                failed_symbols.append(symbol)
                continue
            
            successful_symbols += 1
            price, signal = result
            
            if price is None:
                continue
            
            # Log current state
            logger.debug(f"[{symbol}] Price: ${price:,.2f}")
            
            # Execute if we have a strong signal
            if signal and signal.is_actionable:
                signals_found += 1
                await self.execute_signal(symbol, signal, price)
        
        # Diagnostic log for failed symbols
        if failed_symbols:
            logger.warning(f"Failed to analyze {len(failed_symbols)} symbols: {failed_symbols[:5]}{'...' if len(failed_symbols) > 5 else ''}")
        
        # Summary log
        logger.info(
            f"[BALANCE] Total: ${self.total_balance:,.2f} | "
            f"Free: ${self.free_balance:,.2f} | "
            f"Positions: {len(self.open_positions)}/{self.risk_manager.config.max_open_positions} | "
            f"Analyzed: {successful_symbols}/{len(self.symbols)} | "
            f"Signals: {signals_found} | Daily Trades: {risk_summary['daily_trades']}"
        )
        
        # Update bot status heartbeat for cloud monitoring
        mode = "paper" if not self.is_live else "live"
        self.storage.update_bot_status(
            status="running",
            open_positions=len(self.open_positions),
            exchange=settings.ACTIVE_EXCHANGE,
            mode=mode
        )
    
    async def run(self):
        """Main bot loop."""
        await self.initialize()
        
        print("\n" + "="*70)
        print("      ANTIGRAVITY TRADING BOT - OPTIMIZED ML STRATEGY")
        print(f"      MODE: {'LIVE TRADING' if self.is_live else 'PAPER TRADING (REAL PRICES)'}")
        print(f"      SYMBOLS: {len(self.symbols)} | INITIAL BALANCE: ${self.total_balance:,.2f}")
        print("="*70 + "\n")
        
        # Trading loop (AGGRESSIVE: faster cycles)
        cycle_interval = settings.TRADING_CYCLE_SECONDS
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
