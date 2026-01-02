import ccxt
from loguru import logger
from src.config.settings import settings

class TradeExecutor:
    def __init__(self):
        exchange_id = settings.ACTIVE_EXCHANGE
        
        if exchange_id == "binance":
            config = {
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
            }
        elif exchange_id == "bybit":
            config = {
                'apiKey': settings.BYBIT_API_KEY,
                'secret': settings.BYBIT_SECRET_KEY,
            }
        else:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        self.exchange = getattr(ccxt, exchange_id)(config)
        
    def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None):
        try:
            order = self.exchange.create_order(symbol, type, side, amount, price)
            logger.info(f"Order created: {order}")
            return order
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None
