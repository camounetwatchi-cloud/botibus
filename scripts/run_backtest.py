#!/usr/bin/env python3
"""
Backtest CLI Script.

Usage:
    python scripts/run_backtest.py --symbols BTC/EUR,ETH/EUR --period 6m
    python scripts/run_backtest.py --stress-test crash_2022
    python scripts/run_backtest.py --compare ml,swing,heuristic
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from src.backtest.engine import BacktestEngine
from src.config.settings import settings


async def main():
    parser = argparse.ArgumentParser(description='Run trading strategy backtest')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (default: all from settings)')
    parser.add_argument('--period', type=str, default='6m', help='Period: 1m, 3m, 6m, 1y')
    parser.add_argument('--start', type=str, help='Start date YYYY-MM-DD (overrides period)')
    parser.add_argument('--end', type=str, help='End date YYYY-MM-DD')
    parser.add_argument('--strategy', type=str, default='ml', help='Strategy: ml, swing, heuristic')
    parser.add_argument('--stress-test', type=str, help='Stress test: crash_2022, rally_2021, sideways_2023')
    parser.add_argument('--compare', type=str, help='Compare strategies (comma-separated)')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--report', action='store_true', help='Generate HTML report')
    args = parser.parse_args()
    
    # Parse period to dates
    period_map = {
        '1m': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365
    }
    
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        days = period_map.get(args.period, 180)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    symbols = args.symbols.split(',') if args.symbols else settings.SYMBOLS
    
    engine = BacktestEngine(initial_capital=args.capital)
    
    logger.info("=" * 60)
    logger.info("🧪 BACKTEST CLI")
    logger.info("=" * 60)
    
    if args.stress_test:
        # Run stress test
        results = await engine.run_stress_test(args.stress_test)
    elif args.compare:
        # Compare multiple strategies
        strategies = args.compare.split(',')
        all_results = {}
        
        for strat in strategies:
            logger.info(f"\n📊 Testing {strat.upper()} strategy...")
            engine = BacktestEngine(initial_capital=args.capital)
            results = await engine.run_backtest(symbols, start_date, end_date, strat)
            all_results[strat] = results['metrics']
        
        # Print comparison
        logger.info("\n" + "=" * 60)
        logger.info("📊 STRATEGY COMPARISON")
        logger.info("=" * 60)
        
        headers = ['Metric', *strategies]
        rows = [
            ('Return (%)', *[f"{all_results[s]['total_return_pct']:.2f}%" for s in strategies]),
            ('Win Rate', *[f"{all_results[s]['win_rate']:.1%}" for s in strategies]),
            ('Sharpe', *[f"{all_results[s]['sharpe_ratio']:.2f}" for s in strategies]),
            ('Max DD', *[f"{all_results[s]['max_drawdown']:.1f}%" for s in strategies]),
            ('Trades', *[f"{all_results[s]['total_trades']}" for s in strategies]),
        ]
        
        # Print table
        col_width = 12
        logger.info(" | ".join(h.ljust(col_width) for h in headers))
        logger.info("-" * (col_width * len(headers) + 3 * (len(headers) - 1)))
        for row in rows:
            logger.info(" | ".join(str(c).ljust(col_width) for c in row))
        
        return
    else:
        # Standard backtest
        results = await engine.run_backtest(symbols, start_date, end_date, args.strategy)
    
    if results and args.report:
        engine.export_report()
    
    # Print minimum requirements check
    if results:
        metrics = results['metrics']
        logger.info("\n" + "=" * 60)
        logger.info("✅ MINIMUM REQUIREMENTS CHECK")
        logger.info("=" * 60)
        
        checks = [
            ('Sharpe Ratio > 0.5', metrics['sharpe_ratio'] > 0.5, f"{metrics['sharpe_ratio']:.2f}"),
            ('Max Drawdown < 25%', metrics['max_drawdown'] < 25, f"{metrics['max_drawdown']:.1f}%"),
            ('Win Rate > 45%', metrics['win_rate'] > 0.45, f"{metrics['win_rate']:.1%}"),
            ('Profit Factor > 1.2', metrics['profit_factor'] > 1.2, f"{metrics['profit_factor']:.2f}"),
        ]
        
        all_pass = True
        for name, passed, value in checks:
            status = "✅" if passed else "❌"
            logger.info(f"   {status} {name}: {value}")
            if not passed:
                all_pass = False
        
        if all_pass:
            logger.info("\n🎉 All minimum requirements PASSED!")
        else:
            logger.info("\n⚠️ Some requirements not met - review strategy parameters")


if __name__ == '__main__':
    asyncio.run(main())
