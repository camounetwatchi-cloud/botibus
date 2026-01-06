import ccxt.pro as ccxt
import asyncio
from loguru import logger
from src.config.settings import settings
from typing import List, Dict
import pandas as pd
from datetime import datetime, timedelta


class DataCollector:
    """Data collector with retry logic for robust API calls."""
    
    # Retry configuration for transient network errors
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # Base delay in seconds (exponential backoff)
    
    def __init__(self, exchange_id: str = None):
        self.exchange_id = exchange_id or settings.ACTIVE_EXCHANGE
        self.exchange = getattr(ccxt, self.exchange_id)()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """Fetch historical OHLCV data with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Retry {attempt + 1}/{self.MAX_RETRIES} for {symbol} after {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Failed to fetch OHLCV for {symbol} {timeframe} after {self.MAX_RETRIES} attempts: {e}")
                    return pd.DataFrame()
        return pd.DataFrame()

    async def close(self):
        await self.exchange.close()
