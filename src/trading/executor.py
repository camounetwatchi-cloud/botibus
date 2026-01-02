import ccxt
from loguru import logger
from src.config.settings import settings

class TradeExecutor:
    def __init__(self, exchange_id: str = 'binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        })
        
    def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None):
        try:
            order = self.exchange.create_order(symbol, type, side, amount, price)
            logger.info(f"Order created: {order}")
            return order
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None
