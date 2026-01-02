import vectorbt as vbt
import pandas as pd
from loguru import logger
from src.config.settings import settings

class BacktestEngine:
    def __init__(self):
        self.initial_capital = 10000
        self.fees = 0.001
        
    def run(self, price_data: pd.DataFrame, signals: pd.DataFrame):
        """Run vectorbt backtest."""
        try:
            portfolio = vbt.Portfolio.from_signals(
                price_data,
                entries=signals['entry'],
                exits=signals['exit'],
                init_cash=self.initial_capital,
                fees=self.fees,
                freq='1h'  # Adjust based on timeframe
            )
            return portfolio
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return None

    def get_metrics(self, portfolio):
        if portfolio is None:
            return {}
        return {
            "total_return": portfolio.total_return(),
            "sharpe_ratio": portfolio.sharpe_ratio(),
            "max_drawdown": portfolio.max_drawdown(),
            "win_rate": portfolio.win_rate()
        }
