"""
Comprehensive Backtesting Engine for Trading Bot.

Features:
- Historical data loading with caching
- Multiple strategy support (ML, Swing, Heuristic)
- Realistic fee and slippage modeling
- Performance metrics (Sharpe, Sortino, Max DD, etc.)
- Stress testing on specific market scenarios
- HTML report generation
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio

import numpy as np
import pandas as pd
from loguru import logger

try:
    import vectorbt as vbt
    VBT_AVAILABLE = True
except ImportError:
    VBT_AVAILABLE = False
    logger.warning("VectorBT not installed - some features unavailable")

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.features.technical import TechnicalFeatures
from src.ml.signal_generator import SignalGenerator


class BacktestEngine:
    """
    Comprehensive backtesting engine for strategy validation.
    
    Supports:
    - Multiple strategies (ml, swing, heuristic)
    - Realistic trading simulation with fees and slippage
    - Performance metrics calculation
    - Stress testing on specific market scenarios
    """
    
    # Kraken realistic fees
    MAKER_FEE = 0.0016  # 0.16%
    TAKER_FEE = 0.0026  # 0.26%
    SLIPPAGE = 0.001    # 0.1% simulated slippage
    
    def __init__(
        self,
        initial_capital: float = 10000,
        max_position_pct: float = 0.10,
        risk_per_trade: float = 0.015,
        stop_loss_pct: float = 0.025,
        take_profit_pct: float = 0.05
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital in EUR
            max_position_pct: Max % of capital per position
            risk_per_trade: Risk % per trade
            stop_loss_pct: Default stop-loss percentage
            take_profit_pct: Default take-profit percentage
        """
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.signal_generator = SignalGenerator()
        self.results = []
        self.trades = []
        
    async def load_historical_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        timeframe: str = '15m',
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical OHLCV data for backtesting.
        
        Args:
            symbols: List of trading pairs
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Candle timeframe
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping symbol -> DataFrame
        """
        import ccxt
        
        cache_dir = Path(__file__).parent.parent.parent / "data" / "historical"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        exchange = ccxt.kraken({'enableRateLimit': True})
        
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
        
        data = {}
        
        for symbol in symbols:
            cache_file = cache_dir / f"{symbol.replace('/', '_')}_{start_date}_{end_date}_{timeframe}.parquet"
            
            if use_cache and cache_file.exists():
                logger.info(f"  Loading cached {symbol}...")
                data[symbol] = pd.read_parquet(cache_file)
                continue
            
            logger.info(f"  Fetching {symbol} from exchange...")
            
            all_candles = []
            current_since = start_ts
            
            while current_since < end_ts:
                try:
                    candles = await asyncio.to_thread(
                        exchange.fetch_ohlcv,
                        symbol, timeframe, current_since, 1000
                    )
                    
                    if not candles:
                        break
                    
                    all_candles.extend(candles)
                    current_since = candles[-1][0] + 1
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
                    break
            
            if all_candles:
                df = pd.DataFrame(
                    all_candles,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df[df['timestamp'] <= datetime.strptime(end_date, "%Y-%m-%d")]
                
                # Add technical features
                df = TechnicalFeatures.add_all_features(df)
                
                data[symbol] = df
                
                # Cache for future use
                df.to_parquet(cache_file)
                logger.info(f"    ✓ {symbol}: {len(df)} candles cached")
        
        return data
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        strategy: str = "ml"
    ) -> pd.DataFrame:
        """
        Generate trading signals for historical data.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading pair
            strategy: 'ml', 'swing', or 'heuristic'
            
        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()
        df['signal'] = 0  # 0 = hold, 1 = buy, -1 = sell
        df['confidence'] = 0.0
        
        min_rows = 50  # Minimum rows needed for indicators
        
        for i in range(min_rows, len(df)):
            window = df.iloc[:i+1]
            
            signal = self.signal_generator.generate(window, symbol)
            
            if signal.action == "BUY" and signal.confidence >= settings.MIN_SIGNAL_CONFIDENCE:
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'confidence'] = signal.confidence
            elif signal.action == "SELL" and signal.confidence >= settings.MIN_SIGNAL_CONFIDENCE:
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'confidence'] = signal.confidence
        
        return df
    
    def simulate_trades(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> List[Dict]:
        """
        Simulate trade execution with realistic conditions.
        
        Args:
            df: DataFrame with signals
            symbol: Trading pair
            
        Returns:
            List of trade dictionaries
        """
        trades = []
        capital = self.initial_capital
        position = None
        
        for i, row in df.iterrows():
            price = row['close']
            
            # Check exit conditions for open position
            if position is not None:
                # Calculate current PnL
                if position['side'] == 'long':
                    pnl_pct = (price - position['entry_price']) / position['entry_price']
                else:
                    pnl_pct = (position['entry_price'] - price) / position['entry_price']
                
                should_close = False
                close_reason = ""
                
                # Stop-loss check
                if pnl_pct <= -self.stop_loss_pct:
                    should_close = True
                    close_reason = "stop_loss"
                # Take-profit check
                elif pnl_pct >= self.take_profit_pct:
                    should_close = True
                    close_reason = "take_profit"
                # Signal reversal
                elif row['signal'] == -1 and position['side'] == 'long':
                    should_close = True
                    close_reason = "signal_reversal"
                elif row['signal'] == 1 and position['side'] == 'short':
                    should_close = True
                    close_reason = "signal_reversal"
                
                if should_close:
                    # Calculate exit price with slippage
                    exit_price = price * (1 - self.SLIPPAGE if position['side'] == 'long' else 1 + self.SLIPPAGE)
                    
                    # Calculate fees
                    exit_fee = position['amount'] * exit_price * self.TAKER_FEE
                    
                    # Calculate final PnL
                    if position['side'] == 'long':
                        gross_pnl = (exit_price - position['entry_price']) * position['amount']
                    else:
                        gross_pnl = (position['entry_price'] - exit_price) * position['amount']
                    
                    net_pnl = gross_pnl - position['entry_fee'] - exit_fee
                    
                    # Record trade
                    trade = {
                        'symbol': symbol,
                        'side': position['side'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_time': row.name if isinstance(row.name, datetime) else row['timestamp'],
                        'exit_price': exit_price,
                        'amount': position['amount'],
                        'gross_pnl': gross_pnl,
                        'fees': position['entry_fee'] + exit_fee,
                        'net_pnl': net_pnl,
                        'pnl_pct': net_pnl / position['cost'] * 100,
                        'close_reason': close_reason,
                        'confidence': position['confidence']
                    }
                    trades.append(trade)
                    capital += net_pnl
                    position = None
            
            # Check entry conditions
            if position is None and row['signal'] != 0:
                side = 'long' if row['signal'] == 1 else 'short'
                
                # Calculate position size
                max_trade = capital * self.max_position_pct
                risk_amount = capital * self.risk_per_trade
                
                # Size based on stop-loss
                position_size = min(risk_amount / self.stop_loss_pct, max_trade)
                
                # Apply slippage to entry
                entry_price = price * (1 + self.SLIPPAGE if side == 'long' else 1 - self.SLIPPAGE)
                amount = position_size / entry_price
                entry_fee = position_size * self.TAKER_FEE
                
                position = {
                    'side': side,
                    'entry_time': row.name if isinstance(row.name, datetime) else row['timestamp'],
                    'entry_price': entry_price,
                    'amount': amount,
                    'cost': position_size,
                    'entry_fee': entry_fee,
                    'confidence': row['confidence']
                }
        
        # Close any remaining position at end
        if position is not None and len(df) > 0:
            last_row = df.iloc[-1]
            price = last_row['close']
            exit_price = price * (1 - self.SLIPPAGE if position['side'] == 'long' else 1 + self.SLIPPAGE)
            exit_fee = position['amount'] * exit_price * self.TAKER_FEE
            
            if position['side'] == 'long':
                gross_pnl = (exit_price - position['entry_price']) * position['amount']
            else:
                gross_pnl = (position['entry_price'] - exit_price) * position['amount']
            
            net_pnl = gross_pnl - position['entry_fee'] - exit_fee
            
            trade = {
                'symbol': symbol,
                'side': position['side'],
                'entry_time': position['entry_time'],
                'entry_price': position['entry_price'],
                'exit_time': last_row.name if isinstance(last_row.name, datetime) else last_row['timestamp'],
                'exit_price': exit_price,
                'amount': position['amount'],
                'gross_pnl': gross_pnl,
                'fees': position['entry_fee'] + exit_fee,
                'net_pnl': net_pnl,
                'pnl_pct': net_pnl / position['cost'] * 100,
                'close_reason': 'end_of_backtest',
                'confidence': position['confidence']
            }
            trades.append(trade)
        
        return trades
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            trades: List of completed trades
            
        Returns:
            Dictionary of performance metrics
        """
        if not trades:
            return {
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'avg_trade_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'avg_duration_hours': 0
            }
        
        df = pd.DataFrame(trades)
        
        # Basic stats
        total_pnl = df['net_pnl'].sum()
        total_trades = len(df)
        winners = df[df['net_pnl'] > 0]
        losers = df[df['net_pnl'] <= 0]
        
        win_rate = len(winners) / total_trades if total_trades > 0 else 0
        
        # Win/Loss metrics
        avg_win = winners['net_pnl'].mean() if len(winners) > 0 else 0
        avg_loss = abs(losers['net_pnl'].mean()) if len(losers) > 0 else 0
        
        # Profit factor
        gross_profit = winners['net_pnl'].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Equity curve for Sharpe/Sortino
        equity = self.initial_capital + df['net_pnl'].cumsum()
        returns = equity.pct_change().dropna()
        
        # Risk-adjusted metrics (annualized for 15-min timeframe)
        periods_per_year = 365 * 24 * 4  # 15-min candles
        rf_rate = 0.02  # Risk-free rate
        
        avg_return = returns.mean()
        std_return = returns.std()
        
        sharpe = (avg_return * periods_per_year - rf_rate) / (std_return * np.sqrt(periods_per_year)) if std_return > 0 else 0
        
        # Sortino (only downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.01
        sortino = (avg_return * periods_per_year - rf_rate) / (downside_std * np.sqrt(periods_per_year)) if downside_std > 0 else 0
        
        # Maximum drawdown
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        max_drawdown = abs(drawdown.min())
        
        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Average trade duration
        if 'entry_time' in df.columns and 'exit_time' in df.columns:
            df['duration'] = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
            avg_duration = df['duration'].mean()
            avg_duration_hours = avg_duration.total_seconds() / 3600 if pd.notna(avg_duration) else 0
        else:
            avg_duration_hours = 0
        
        return {
            'total_return': total_pnl,
            'total_return_pct': (total_pnl / self.initial_capital) * 100,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown * 100,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'avg_duration_hours': avg_duration_hours,
            'total_fees': df['fees'].sum(),
            'winning_trades': len(winners),
            'losing_trades': len(losers)
        }
    
    async def run_backtest(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy: str = "ml"
    ) -> Dict:
        """
        Run complete backtest.
        
        Args:
            symbols: Trading pairs to backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy: Strategy to test
            
        Returns:
            Backtest results dictionary
        """
        logger.info("=" * 60)
        logger.info(f"🔬 BACKTEST: {strategy.upper()} Strategy")
        logger.info(f"   Period: {start_date} to {end_date}")
        logger.info(f"   Symbols: {symbols}")
        logger.info("=" * 60)
        
        # Load data
        logger.info("📊 Loading historical data...")
        data = await self.load_historical_data(symbols, start_date, end_date)
        
        all_trades = []
        
        for symbol in symbols:
            if symbol not in data:
                logger.warning(f"No data for {symbol}")
                continue
            
            df = data[symbol]
            logger.info(f"📈 Processing {symbol} ({len(df)} candles)...")
            
            # Generate signals
            df = self.generate_signals(df, symbol, strategy)
            
            # Simulate trades
            trades = self.simulate_trades(df, symbol)
            all_trades.extend(trades)
            
            logger.info(f"   Trades: {len(trades)}")
        
        # Calculate overall metrics
        metrics = self.calculate_metrics(all_trades)
        
        # Store results
        self.trades = all_trades
        self.results = {
            'strategy': strategy,
            'start_date': start_date,
            'end_date': end_date,
            'symbols': symbols,
            'metrics': metrics,
            'trades': all_trades
        }
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 BACKTEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"   Total Return: €{metrics['total_return']:.2f} ({metrics['total_return_pct']:.2f}%)")
        logger.info(f"   Total Trades: {metrics['total_trades']}")
        logger.info(f"   Win Rate: {metrics['win_rate']:.2%}")
        logger.info(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        logger.info(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"   Max Drawdown: {metrics['max_drawdown']:.2f}%")
        logger.info(f"   Avg Trade: €{metrics['avg_trade_pnl']:.2f}")
        logger.info(f"   Total Fees: €{metrics['total_fees']:.2f}")
        logger.info("=" * 60)
        
        return self.results
    
    async def run_stress_test(
        self,
        scenario: str = "crash_2022"
    ) -> Dict:
        """
        Run backtest on specific stress scenarios.
        
        Args:
            scenario: 'crash_2022', 'rally_2021', 'sideways_2023'
            
        Returns:
            Backtest results
        """
        scenarios = {
            'crash_2022': {
                'start': '2022-05-01',
                'end': '2022-07-01',
                'description': 'May-June 2022 Crypto Crash (BTC -40%)'
            },
            'rally_2021': {
                'start': '2021-10-01',
                'end': '2021-11-15',
                'description': 'October-November 2021 Bull Run'
            },
            'sideways_2023': {
                'start': '2023-03-01',
                'end': '2023-06-01',
                'description': '2023 Q2 Consolidation'
            }
        }
        
        if scenario not in scenarios:
            logger.error(f"Unknown scenario: {scenario}")
            return {}
        
        config = scenarios[scenario]
        logger.info(f"🔥 STRESS TEST: {config['description']}")
        
        # Use top 4 volatile coins for stress test
        symbols = ['BTC/EUR', 'ETH/EUR', 'SOL/EUR', 'XRP/EUR']
        
        return await self.run_backtest(
            symbols,
            config['start'],
            config['end'],
            strategy='ml'
        )
    
    def export_report(self, output_path: str = None) -> str:
        """
        Export HTML report with charts.
        
        Args:
            output_path: Path to save report
            
        Returns:
            Path to generated report
        """
        if not self.results:
            logger.error("No backtest results to export")
            return ""
        
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent / "logs" / "backtest_report.html"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        metrics = self.results['metrics']
        trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        
        # Generate simple HTML report
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backtest Report - {self.results['strategy'].upper()}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #4ecca3; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .metric {{ background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4ecca3; }}
        .metric-label {{ color: #888; margin-top: 5px; }}
        .positive {{ color: #4ecca3; }}
        .negative {{ color: #ff6b6b; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #16213e; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Backtest Report</h1>
        <p>Strategy: {self.results['strategy'].upper()} | Period: {self.results['start_date']} to {self.results['end_date']}</p>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value {'positive' if metrics['total_return'] >= 0 else 'negative'}">
                    €{metrics['total_return']:.2f}
                </div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['win_rate']:.1%}</div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['profit_factor']:.2f}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['sharpe_ratio']:.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric">
                <div class="metric-value negative">{metrics['max_drawdown']:.1f}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['total_trades']}</div>
                <div class="metric-label">Total Trades</div>
            </div>
            <div class="metric">
                <div class="metric-value">€{metrics['avg_win']:.2f}</div>
                <div class="metric-label">Avg Win</div>
            </div>
            <div class="metric">
                <div class="metric-value negative">€{metrics['avg_loss']:.2f}</div>
                <div class="metric-label">Avg Loss</div>
            </div>
        </div>
        
        <h2>Trade History ({len(self.trades)} trades)</h2>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>PnL</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for trade in self.trades[-50:]:  # Last 50 trades
            pnl_class = 'positive' if trade['net_pnl'] >= 0 else 'negative'
            html += f"""
                <tr>
                    <td>{trade['symbol']}</td>
                    <td>{trade['side'].upper()}</td>
                    <td>€{trade['entry_price']:.2f}</td>
                    <td>€{trade['exit_price']:.2f}</td>
                    <td class="{pnl_class}">€{trade['net_pnl']:.2f}</td>
                    <td>{trade['close_reason']}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"📄 Report saved to {output_path}")
        return str(output_path)


# Standalone usage
if __name__ == "__main__":
    import argparse
    
    async def main():
        parser = argparse.ArgumentParser(description='Run backtest')
        parser.add_argument('--symbols', type=str, default='BTC/EUR,ETH/EUR')
        parser.add_argument('--start', type=str, default='2024-07-01')
        parser.add_argument('--end', type=str, default='2025-01-01')
        parser.add_argument('--strategy', type=str, default='ml')
        parser.add_argument('--stress-test', type=str, help='Run stress test scenario')
        args = parser.parse_args()
        
        engine = BacktestEngine()
        
        if args.stress_test:
            results = await engine.run_stress_test(args.stress_test)
        else:
            symbols = args.symbols.split(',')
            results = await engine.run_backtest(symbols, args.start, args.end, args.strategy)
        
        if results:
            engine.export_report()
    
    asyncio.run(main())
