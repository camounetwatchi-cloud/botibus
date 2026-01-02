from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path

class Settings(BaseSettings):
    # Exchange Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_SECRET_KEY: Optional[str] = None

    # Database
    DATABASE_URL: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # System
    LOG_LEVEL: str = "INFO"
    DEVICE: str = "cuda"
    DATA_PATH: Path = Path("./data")
    MODELS_PATH: Path = Path("./models")

    # Trading Defaults
    TIMEFRAMES: List[str] = ["15m", "1h", "4h", "1d"]
    SYMBOLS: List[str] = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", 
        "SOL/USDT", "NEAR/USDT", "TRX/USDT", "DOGE/USDT", 
        "ADA/USDT", "SUI/USDT"
    ]
    
    # === OPTIMIZED TRADING PARAMETERS ===
    # Position Sizing
    MAX_POSITION_PERCENT: float = 0.15       # Max 15% per position
    MIN_TRADE_VALUE: float = 100.0           # Minimum $100 per trade
    RISK_PER_TRADE: float = 0.02             # Risk 2% per trade
    
    # Risk Management
    DEFAULT_STOP_LOSS: float = 0.025         # 2.5% stop loss
    DEFAULT_TAKE_PROFIT: float = 0.045       # 4.5% take profit
    MAX_DAILY_TRADES: int = 9999               # Effectively unlimited
    COOLDOWN_MINUTES: int = 30               # Between trades per symbol
    MAX_OPEN_POSITIONS: int = 5              # Max concurrent positions
    MAX_DAILY_LOSS: float = 0.05             # Stop trading at -5% daily
    
    # Signal Thresholds
    MIN_SIGNAL_CONFIDENCE: float = 0.55      # Minimum confidence to trade
    STRONG_SIGNAL_THRESHOLD: float = 0.75    # Strong signal threshold
    
    # Trading Fees
    MAKER_FEE: float = 0.001                 # 0.1% maker fee
    TAKER_FEE: float = 0.001                 # 0.1% taker fee
    
    # Cycle Timing
    TRADING_CYCLE_SECONDS: int = 60          # Seconds between cycles
    DATA_FETCH_LIMIT: int = 200              # Candles to fetch

    class Config:
        env_file = ".env"

settings = Settings()

