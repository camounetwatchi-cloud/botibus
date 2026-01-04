import ccxt.pro as ccxt
import asyncio
from loguru import logger
from src.config.settings import settings
from typing import List, Dict
import pandas as pd
from datetime import datetime, timedelta

class DataCollector:
    def __init__(self, exchange_id: str = None):
        self.exchange_id = exchange_id or settings.ACTIVE_EXCHANGE
        self.exchange = getattr(ccxt, self.exchange_id)()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    async def close(self):
        await self.exchange.close()
