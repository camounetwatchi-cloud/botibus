"""
GitHub Actions Trading Script.
Runs exactly one trading cycle and exits.
Used for 24/7 automation without a permanent VPS.
"""
import asyncio
import sys
from loguru import logger
from scripts.live_trade import OptimizedTradingBot

# Configure logging for CI
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

async def run_once():
    """Initialize bot, run one cycle, and cleanup."""
    logger.info("Starting GitHub Actions trading cycle...")
    
    bot = OptimizedTradingBot()
    
    try:
        # 1. Warm up (fetch history, load positions)
        await bot.initialize()
        
        # 2. Run the trading logic once
        await bot.run_cycle()
        
        logger.info("Cycle completed successfully.")
        
    except Exception as e:
        logger.error(f"Critical error during GH Action cycle: {e}")
        sys.exit(1)
    finally:
        # 3. Explicitly close connections
        await bot.collector.close()
        logger.info("Connections closed. exiting.")

if __name__ == "__main__":
    asyncio.run(run_once())
