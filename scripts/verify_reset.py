import sys
from pathlib import Path
from loguru import logger

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.storage import DataStorage

def verify_reset():
    storage = DataStorage()
    
    # Check Balance
    balance = storage.get_latest_balance()
    logger.info(f"Current Balance: {balance}")
    
    if balance.get('total') == 1000.0 and balance.get('free') == 1000.0:
        logger.info("✅ Balance verification passed ($1000).")
    else:
        logger.error(f"❌ Balance verification failed! Expected $1000, got {balance}")
    
    # Check Trades
    trades = storage.get_trades()
    logger.info(f"Number of trades: {len(trades)}")
    
    if len(trades) == 0:
        logger.info("✅ Trade history verification passed (Empty).")
    else:
        logger.error(f"❌ Trade history verification failed! Expected 0, got {len(trades)}")
        
    # Check Bot Status
    status = storage.get_bot_status()
    logger.info(f"Bot Status: {status}")
    
    if status.get('open_positions') == 0:
        logger.info("✅ Bot status verification passed (0 positions).")
    else:
        logger.error(f"❌ Bot status verification failed! Expected 0 positions, got {status.get('open_positions')}")

if __name__ == "__main__":
    verify_reset()
