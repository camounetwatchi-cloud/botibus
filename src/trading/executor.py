import ccxt
from loguru import logger
from typing import Optional, Dict, Any
from src.config.settings import settings

class TradeExecutor:
    """
    Handles execution of trades on the configured exchange (Kraken or Binance).
    """
    def __init__(self):
        """
        Initialize the TradeExecutor.
        
        Raises:
            ValueError: If the exchange configured in settings is not supported.
        """
        exchange_id = settings.ACTIVE_EXCHANGE
        
        if exchange_id == "binance":
            config = {
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
            }
        elif exchange_id == "kraken":
            config = {
                'apiKey': settings.KRAKEN_API_KEY,
                'secret': settings.KRAKEN_SECRET_KEY,
            }
        else:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        self.exchange = getattr(ccxt, exchange_id)(config)
        
    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Creates a new order on the exchange.

        Args:
            symbol (str): The trading pair (e.g., 'BTC/USDT').
            type (str): Order type ('limit' or 'market').
            side (str): Order side ('buy' or 'sell').
            amount (float): Amount of base currency to trade.
            price (float, optional): Price for limit orders. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: The order response from the exchange, or None if failed.
        """
        import asyncio
        try:
            # Run blocking ccxt call in a separate thread
            order = await asyncio.to_thread(
                self.exchange.create_order, 
                symbol, type, side, amount, price
            )
            logger.info(f"Order created: {order}")
            return order
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None
