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
from src.ml.strategy_orchestrator import StrategyOrchestrator, OrchestratedSignal as MLSignal
from src.trading.risk_manager import RiskManager, RiskConfig
from src.trading.fee_calculator import fee_calculator
from src.learning.performance import PerformanceAnalyzer
from src.learning.auto_learner import AutoLearner
from src.monitoring.telegram_notifier import TelegramNotifier


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
        self.signal_generator = StrategyOrchestrator()
        self.performance_analyzer = PerformanceAnalyzer(self.storage)
        
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
        
        # Initialize Telegram notifier
        self.notifier = TelegramNotifier()
        
        # Initialize auto-learner (for confidence adjustments and blacklist)
        self.auto_learner = AutoLearner(self.storage)
            
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
        
        # Track last balance update for periodic history logging (every 1 hour)
        self.last_balance_update = datetime.now()
        
        # Track last auto-learning run
        self.last_learning_run = datetime.now()
        
        logger.info(f"Trading symbols: {self.symbols}")
    
    async def initialize(self):
        """Warm up the bot with historical data."""
        logger.info("[INIT] Initializing bot with historical data...")
        
        # Update balance in DB
        await asyncio.to_thread(self.storage.update_balance, self.total_balance, self.free_balance, self.used_balance)
        
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
        """Close a position and update records with all fees."""
        if trade_id not in self.open_positions:
            return
        
        position = self.open_positions[trade_id]
        symbol = position['symbol']
        amount = position['amount']
        entry_price = position['entry_price']
        entry_time = position.get('entry_time', datetime.now())
        
        # Calculate all fees using FeeCalculator
        fees = fee_calculator.calculate_all_fees_for_trade(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            entry_time=entry_time,
            exit_time=datetime.now(),
            is_margin=True
        )
        
        # Gross PnL (before fees)
        gross_pnl = pnl
        
        # Net PnL (after all fees)
        net_pnl = gross_pnl - fees['total_fees']
        
        # Update trade record with comprehensive fee data
        trade_update = {
            "id": trade_id,
            "status": "closed",
            "exit_price": exit_price,
            "exit_time": pd.Timestamp.now(),
            "pnl": net_pnl,  # Keep backward compatibility
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "entry_fee": fees['entry_fee'],
            "exit_fee": fees['exit_fee'],
            "rollover_fee": fees['rollover_fee'],
            "total_fees": fees['total_fees']
        }
        await asyncio.to_thread(self.storage.save_trade, trade_update)
        
        # Update balance (use net PnL)
        self.free_balance += (amount * entry_price) + net_pnl
        self.used_balance -= (amount * entry_price)
        self.total_balance = self.free_balance + self.used_balance
        await asyncio.to_thread(self.storage.update_balance, self.total_balance, self.free_balance, self.used_balance)
        
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
            f"Entry: ${entry_price:,.2f} -> Exit: ${exit_price:,.2f}"
        )
        logger.info(
            f"   Gross: ${gross_pnl:+,.2f} | Fees: ${fees['total_fees']:.2f} "
            f"(Entry: ${fees['entry_fee']:.2f}, Exit: ${fees['exit_fee']:.2f}, Rollover: ${fees['rollover_fee']:.2f}) | "
            f"Net: ${net_pnl:+,.2f} ({reason})"
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
        
        # Get Kelly fraction for intelligent position sizing
        kelly_fraction = self.performance_analyzer.calculate_kelly_fraction(
            symbol, 
            lookback_trades=settings.KELLY_LOOKBACK_TRADES
        )
        
        # Adjust confidence based on symbol performance history
        adjusted_confidence = self.performance_analyzer.get_confidence_adjustment(
            symbol, signal.confidence
        )
        
        # Calculate position size with dynamic TP and Kelly sizing
        position_size, stop_loss, take_profit = self.risk_manager.calculate_position_size(
            balance=self.free_balance,
            price=current_price,
            confidence=adjusted_confidence,
            atr=atr,
            kelly_fraction=kelly_fraction
        )
        
        if position_size <= 0:
            logger.info(f"[{symbol}] Position size too small")
            return
        
        # Apply STRONG signal multiplier for high-confidence confluence
        signal_strength = getattr(signal, 'signal_strength', 'NORMAL')
        if signal_strength == "STRONG":
            position_size *= settings.STRONG_SIGNAL_SIZE_MULTIPLIER
            logger.info(f"[{symbol}] ⚡ STRONG signal - size x{settings.STRONG_SIGNAL_SIZE_MULTIPLIER}")
        
        # Calculate trade value and entry fees
        trade_value = position_size * current_price
        entry_fees = fee_calculator.calculate_entry_fees(trade_value, is_margin=True)
        
        # Create trade record with entry fee
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
            "fee": entry_fees['total'],  # Backward compat
            "entry_fee": entry_fees['total'],
            "exit_fee": 0.0,
            "rollover_fee": 0.0,
            "total_fees": entry_fees['total'],
            "gross_pnl": 0.0,
            "net_pnl": 0.0
        }
        
        # Save trade
        await asyncio.to_thread(self.storage.save_trade, trade_data)
        
        # Update balance (deduct trade value AND entry fees from free balance)
        self.free_balance -= (trade_value + entry_fees['total'])
        self.used_balance += trade_value
        self.total_balance = self.free_balance + self.used_balance
        await asyncio.to_thread(self.storage.update_balance, self.total_balance, self.free_balance, self.used_balance)
        
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
            'entry_fee': entry_fees['total'],
        }
        
        # Save cooldown to database for persistence across restarts
        await asyncio.to_thread(self.storage.save_cooldown, symbol, datetime.now())
        
        # Initialize peak price tracking
        self.position_peaks[trade_id] = current_price
        
        # Calculate TP percentage for logging
        tp_pct = ((take_profit - current_price) / current_price) * 100
        
        # Log with Kelly info if used
        kelly_info = f"Kelly: {kelly_fraction:.1%} | " if kelly_fraction > 0 else ""
        logger.info(
            f"[OPEN] {side.upper()} {symbol} | "
            f"Size: {position_size:.6f} @ ${current_price:,.2f} | "
            f"Value: ${trade_value:,.2f} | {kelly_info}Confidence: {adjusted_confidence:.0%}"
        )
        logger.info(f"   Entry Fee: ${entry_fees['total']:.2f} | Reasons: {', '.join(signal.reasons[:3])}")
        logger.info(f"   SL: ${stop_loss:,.2f} (-2.5%) | TP: ${take_profit:,.2f} (+{tp_pct:.1f}%)")

        # --- PYRAMIDING SAFETY: Move SL of existing positions to Breakeven ---
        for tid, pos in self.open_positions.items():
            if pos['symbol'] == symbol and tid != trade_id:
                # Existing position for same symbol
                
                # Only apply if same direction (Pyramiding)
                if pos['side'] == side:
                    old_sl = pos.get('stop_loss', 0)
                    entry = pos['entry_price']
                    
                    # Logic: Ensure SL is at least at Entry Price (Breakeven)
                    # If we already have a Trailing Stop higher than Entry, keep it.
                    
                    if side == 'buy':
                        new_sl = max(old_sl, entry)
                        if new_sl > old_sl:
                            pos['stop_loss'] = new_sl
                            if tid in self.risk_manager.state.open_positions:
                                self.risk_manager.state.open_positions[tid].stop_loss = new_sl
                            logger.info(f"[{symbol}] Pyramiding Safety: Moved SL of {tid} to Breakeven (${new_sl:.2f})")
                            
                    elif side == 'sell':
                        # For shorts, SL should be <= Entry. So min(old_sl, entry)
                        # But 'stop_loss' for short is a PRICE > Entry.
                        # Wait, Short SL is ABOVE entry.
                        # Breakeven for Short is lowering SL to Entry Price.
                        # So we want new_sl = min(old_sl, entry)
                        
                        # Stop Loss for Short: Start at 1.025 * Entry.
                        # We want to move it down to Entry.
                        
                        # If old_sl is 0 (uninitialized?), careful.
                        if old_sl == 0: old_sl = entry * 1.5 # Safety
                        
                        new_sl = min(old_sl, entry)
                        if new_sl < old_sl:
                             pos['stop_loss'] = new_sl
                             if tid in self.risk_manager.state.open_positions:
                                self.risk_manager.state.open_positions[tid].stop_loss = new_sl
                             logger.info(f"[{symbol}] Pyramiding Safety: Moved SL of {tid} to Breakeven (${new_sl:.2f})")
    
    async def run_cycle(self):
        """
        Run one trading cycle with Arbitrage and Unlimited Positions logic.
        
        Steps:
        1. Check Risk Limits (Daily loss, etc).
        2. Manage Open Positions (SL/TP/Trailing).
        3. Batch Analysis: Analyze ALL symbols to get current scores.
        4. Natural Exits: Close positions that have turned to SELL signal.
        5. Arbitrage & Entry:
           - Sort new buying opportunities by confidence.
           - If funds available -> BUY.
           - If no funds -> Check if New_Signal is significantly better than Weakest_Position.
           - If yes -> SWAP (Close weak, Open new).
        """
        logger.debug("Starting trading cycle...")
        
        # --- 1. Risk Limits ---
        self.risk_manager.reset_daily_stats()
        risk_summary = self.risk_manager.get_risk_summary()
        
        if not risk_summary['can_trade']:
            logger.warning("Trading paused due to risk limits (Daily loss/trades reached)")
            return
        
        # --- 2. Manage Open Positions (Hard Stops/TP) ---
        
        # --- 3. Batch Analysis ---
        # We need fresh analysis for ALL symbols (both watchlist and current holdings)
        # to compare their relative strength.
        symbols_to_analyze = list(set(self.symbols + [p['symbol'] for p in self.open_positions.values()]))
        
        # PARALLEL analysis
        results = await asyncio.gather(*[
            self.fetch_and_analyze(symbol) 
            for symbol in symbols_to_analyze
        ], return_exceptions=True)
        
        # Organized results
        analysis_map = {}  # symbol -> (price, signal)
        
        successful_symbols = 0
        failed_symbols = []
        
        for symbol, result in zip(symbols_to_analyze, results):
            if isinstance(result, Exception):
                failed_symbols.append(symbol)
                continue
            
            price, signal = result
            if price is None or signal is None:
                continue
                
            analysis_map[symbol] = (price, signal)
            successful_symbols += 1
            
            # Log current state
            logger.debug(f"[{symbol}] ${price:,.2f} | Signal: {signal.action} ({signal.confidence:.0%})")

        if failed_symbols:
            logger.warning(f"Failed to analyze {len(failed_symbols)} symbols: {failed_symbols[:5]}")

        # --- 3b. Manage Open Positions (Hard Stops/TP) ---
        # Now that we have fresh prices in self.price_cache (updated by fetch_and_analyze),
        # we check safety exits BEFORE strategic exits.
        await self.check_open_positions()

        # --- 4. Natural Exits (Signal flipped to SELL) ---
        # Close positions that are no longer supported by strategy, regardless of PnL
        current_holdings = list(self.open_positions.keys()) # Copy keys
        for trade_id in current_holdings:
            pos = self.open_positions[trade_id]
            symbol = pos['symbol']
            
            if symbol in analysis_map:
                price, signal = analysis_map[symbol]
                # If signal is SELL or STRONG_SELL, close it standardly
                if signal.action == "SELL" and pos['side'] == 'buy':
                    logger.info(f"[{symbol}] Natural Exit triggered by SELL signal (Closing LONG)")
                    # Calculate approximate PnL for logging content
                    entry = pos['entry_price']
                    pnl = (price - entry) * pos['amount']
                    await self.close_position(trade_id, price, "SIGNAL_EXIT_LONG", pnl)
                elif signal.action == "BUY" and pos['side'] == 'sell':
                    logger.info(f"[{symbol}] Natural Exit triggered by BUY signal (Closing SHORT)")
                    # Calculate approximate PnL for logging content
                    entry = pos['entry_price']
                    pnl = (entry - price) * pos['amount']
                    await self.close_position(trade_id, price, "SIGNAL_EXIT_SHORT", pnl)

        # --- 5. Arbitrage & Entry Logic ---
        
        # Identify Candidates
        # A. New Opportunities (Strong Buy/Buy, not currently held)
        opportunities = []
        # B. Existing Holdings (For potential swapping)
        weakest_holdings = []
        
        held_symbols = {p['symbol'] for p in self.open_positions.values()}
        
        for symbol, (price, signal) in analysis_map.items():
            # Potential Entry (BUY or SHORT opportunity) - CHECK ALL, even if held (Pyramiding)
            if signal.is_actionable:
                if signal.action == "BUY":
                    opportunities.append({
                        'symbol': symbol,
                        'price': price,
                        'signal': signal,
                        'score': signal.confidence,
                        'direction': 'buy'
                    })
                elif signal.action == "SELL":
                    # SHORT opportunity - margin trading allows shorting
                    opportunities.append({
                        'symbol': symbol,
                        'price': price,
                        'signal': signal,
                        'score': signal.confidence,
                        'direction': 'sell'  # Mark as short
                    })
            
            # Also check for Weakest Holdings (for Arbitrage)
            if symbol in held_symbols:
                # Existing Holding - track its score for comparison
                # Find the trade_id for this symbol
                trade_id = next((tid for tid, p in self.open_positions.items() if p['symbol'] == symbol), None)
                if trade_id:
                    weakest_holdings.append({
                        'trade_id': trade_id,
                        'symbol': symbol,
                        'price': price,
                        'score': signal.confidence
                    })
        
        # Sort lists
        # Best new opportunities first
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        # Weakest holdings first
        weakest_holdings.sort(key=lambda x: x['score'], reverse=False)
        
        # Account for swap friction: close + open = ~0.44% fee drag + slippage
        # New signal must be significantly better to justify this cost
        SWAP_THRESHOLD = 0.25  # Raised from 0.15 to account for double-fee friction
        
        # Iterate through best opportunities
        for opp in opportunities:
            symbol = opp['symbol']
            signal = opp['signal']
            price = opp['price']
            
            # Check if we can open trade simply (Capital check)
            # We use total_balance check in RiskManager, but here we specifically want to know if we have FREE funds
            # RiskManager.can_trade checks limits, but we removed position limit.
            # We just need to check if we have enough cash.
            
            can_trade_risk, risk_reason = self.risk_manager.can_trade(symbol, self.total_balance)
            
            # Calculate position size to see if we have enough money
            # (We need to DRY this logic, relying on risk_manager.calculate_position_size)
            atr = getattr(signal, 'atr', 0) or self.atr_cache.get(symbol, 0)
            
            pos_size, _, _ = self.risk_manager.calculate_position_size(
                balance=self.free_balance,
                price=price,
                confidence=signal.confidence,
                atr=atr
            )
            
            cost = pos_size * price
            
            if can_trade_risk and cost > 0:

                # CASE A: We have funds -> Just Open
                await self.execute_signal(symbol, signal, price)
                # Update free balance available for next iteration in loop?
                # execute_signal updates self.free_balance
                continue
            
            elif "Daily" in risk_reason or "Cooldown" in risk_reason:
                # Hard blocks from risk manager, skip
                continue
            
            else:
                # CASE B: Insufficient Funds -> ARBITRAGE CHECK
                # Try to find a weak position to swap
                
                # If we have no holdings, we just can't trade (weird but possible if min_trade > free_balance)
                if not weakest_holdings:
                    continue
                    
                # Look at the weakest holding
                victim = weakest_holdings[0]
                
                # Check metrics: Is New significantly better than Old?
                score_diff = opp['score'] - victim['score']
                
                if score_diff > SWAP_THRESHOLD:
                    logger.info(f"⚡ ARBITRAGE OPPORTUNITY: Swapping {victim['symbol']} ({victim['score']:.2f}) for {symbol} ({opp['score']:.2f}) | Diff: {score_diff:.2f}")
                    
                    # 1. Close Victim
                    # Recalculate PnL
                    victim_pos = self.open_positions[victim['trade_id']]
                    pnl = (victim['price'] - victim_pos['entry_price']) * victim_pos['amount']
                    if victim_pos['side'] == 'sell':
                        pnl = -pnl
                        
                    await self.close_position(victim['trade_id'], victim['price'], "ARBITRAGE_SWAP", pnl)
                    
                    # Remove from local list so we don't try to close it again this cycle
                    weakest_holdings.pop(0)
                    
                    # 2. Open New
                    # Now we should have funds (updated in close_position)
                    # We need to re-check risk/size because balance changed
                     # Get ATR for dynamic TP calculation
                    atr = getattr(signal, 'atr', 0) or self.atr_cache.get(symbol, 0)
                    
                    # Recalculate with new balance
                    new_size, _, _ = self.risk_manager.calculate_position_size(
                        balance=self.free_balance,
                        price=price, 
                        confidence=signal.confidence,
                        atr=atr
                    )
                    
                    if new_size * price >= settings.MIN_TRADE_VALUE:
                        await self.execute_signal(symbol, signal, price)
                    else:
                        logger.warning(f"Swap executed but insufficient funds for new trade? Free: {self.free_balance}")
                else:
                    # If this opportunity isn't better than our WORST holding, 
                    # it definitely isn't better than the others.
                    # And since opportunities are sorted best-first, we can likely stop trying to swap?
                    # No, maybe the NEXT opportunity is smaller but we still don't have funds.
                    # But we are iterating on opportunities.
                    logger.debug(f"Skipping swap: {symbol} ({opp['score']:.2f}) not enough > {victim['symbol']} ({victim['score']:.2f})")
        
        # Summary log
        logger.info(
            f"[BALANCE] Total: ${self.total_balance:,.2f} | "
            f"Free: ${self.free_balance:,.2f} | "
            f"Positions: {len(self.open_positions)} | "
            f"Active Analysis: {successful_symbols} symbols"
        )
        
        # Update bot status heartbeat
        mode = "paper" if not self.is_live else "live"
        await asyncio.to_thread(
            self.storage.update_bot_status,
            status="running",
            open_positions=len(self.open_positions),
            exchange=settings.ACTIVE_EXCHANGE,
            mode=mode
        )
        
        # Periodic balance snapshot
        if datetime.now() - self.last_balance_update > timedelta(hours=1):
            await asyncio.to_thread(self.storage.update_balance, self.total_balance, self.free_balance, self.used_balance)
            self.last_balance_update = datetime.now()
            
        # --- 6. Daily Auto-Learning (Every 24h) ---
        if datetime.now() - self.last_learning_run > timedelta(hours=24):
            logger.info("🧠 Triggering Daily Auto-Learning...")
            try:
                # Run analysis
                adjustments = await asyncio.to_thread(self.auto_learner.run_daily_analysis)
                
                # Send report via Telegram
                report = self.auto_learner.get_insights_report()
                await self.notifier._send(f"<pre>{report}</pre>", parse_mode="HTML")
                
                # Notify specifically about blacklist/confidence changes
                if adjustments.get('blacklist_changes'):
                    await self.notifier.alert_critical(
                        f"Auto-Learner: Blacklist updated!\n{adjustments['blacklist_changes']}", 
                        alert_type='warning'
                    )
                
                self.last_learning_run = datetime.now()
                
            except Exception as e:
                logger.error(f"Auto-learning failed: {e}")
    
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
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(f"CRASH TIME: {datetime.now()}\n")
            f.write(traceback.format_exc())
        print("CRASH DETECTED! Saved to crash_log.txt")
        # Keep window open for a moment
        import time
        time.sleep(10)
