import os
import sys
from datetime import datetime
from loguru import logger
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.data.storage import DataStorage
from src.trading.executor import TradeExecutor

def reset_to_clean_slate():
    logger.info("🚀 Starting Clean Slate Reset...")
    
    # 1. Initialize Storage
    storage = DataStorage()
    
    # 2. Close Live Positions (if applicable)
    if not settings.PAPER_TRADING:
        logger.warning("⚠️ LIVE MODE detected. Closing all positions on exchange...")
        try:
            executor = TradeExecutor()
            # Cancel all open orders
            logger.info("Canceling all open orders...")
            executor.exchange.cancel_all_orders()
            
            # Fetch and close all positions
            # Note: CCXT position handling varies by exchange. 
            # For Kraken/Binance/Bybit, we'll try to fetch positions.
            if hasattr(executor.exchange, 'fetch_positions'):
                positions = executor.exchange.fetch_positions()
                for pos in positions:
                    symbol = pos['symbol']
                    amount = float(pos['contracts']) if 'contracts' in pos else float(pos['amount'])
                    if amount != 0:
                        side = 'sell' if amount > 0 else 'buy'
                        logger.info(f"Closing position: {symbol} ({amount})")
                        executor.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=abs(amount)
                        )
            else:
                # Fallback for exchanges without fetch_positions (like Kraken Spot)
                logger.info("Exchange does not support fetch_positions, checking balances...")
                balances = executor.exchange.fetch_balance()
                for asset, data in balances['total'].items():
                    if asset in ['USD', 'USDC', 'EUR', 'USDT']:
                        continue
                    if data > 0:
                        # Find a symbol to sell against (prefer EUR/USDC/USDT)
                        potential_symbols = [f"{asset}/EUR", f"{asset}/USDC", f"{asset}/USDT", f"{asset}/USD"]
                        markets = executor.exchange.fetch_markets()
                        market_symbols = [m['symbol'] for m in markets]
                        
                        target_symbol = None
                        for s in potential_symbols:
                            if s in market_symbols:
                                target_symbol = s
                                break
                        
                        if target_symbol:
                            logger.info(f"Closing asset balance: {asset} ({data}) via {target_symbol}")
                            executor.create_order(
                                symbol=target_symbol,
                                type='market',
                                side='sell',
                                amount=data
                            )
        except Exception as e:
            logger.error(f"Error closing live positions: {e}")
            logger.warning("Continuing with database reset anyway...")
    else:
        logger.info("📝 Paper trading mode / No live cleanup needed.")

    # 3. Reset Database History
    logger.info("🧹 Clearing database tables (trades, balance)...")
    try:
        with storage._get_connection() as conn:
            if storage.use_postgres:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM trades")
                cursor.execute("DELETE FROM balance")
                conn.commit()
            else:
                conn.execute("DELETE FROM trades")
                conn.execute("DELETE FROM balance")
        logger.info("✅ Database history cleared.")
    except Exception as e:
        logger.error(f"Error clearing database: {e}")

    # 4. Set Initial Capital to $1000
    logger.info("💰 Setting initial capital to $1000...")
    try:
        storage.update_balance(total=1000.0, free=1000.0, used=0.0)
        logger.info("✅ Balance initialized to $1000.")
    except Exception as e:
        logger.error(f"Error initializing balance: {e}")

    # 5. Reset Bot Status
    logger.info("🤖 Resetting bot status...")
    try:
        storage.update_bot_status(
            status="online", 
            open_positions=0, 
            exchange=settings.ACTIVE_EXCHANGE,
            mode="paper" if settings.PAPER_TRADING else "live"
        )
        logger.info("✅ Bot status reset.")
    except Exception as e:
        logger.error(f"Error resetting bot status: {e}")

    logger.info("✨ Clean Slate Reset Complete! The bot is now ready to start fresh.")

if __name__ == "__main__":
    confirm = input("Are you sure you want to PERMANENTLY reset the bot and capital? (y/n): ")
    if confirm.lower() == 'y':
        reset_to_clean_slate()
    else:
        logger.info("Reset cancelled.")
