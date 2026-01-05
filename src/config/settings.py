from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path

class Settings(BaseSettings):
    # Exchange Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_SECRET_KEY: Optional[str] = None
    KRAKEN_API_KEY: Optional[str] = None
    KRAKEN_SECRET_KEY: Optional[str] = None

    # Database
    DATABASE_URL: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # System
    ACTIVE_EXCHANGE: str = "kraken"  # 'binance', 'bybit' or 'kraken'
    PAPER_TRADING: bool = False      # Default to Real Trading (Safety: requires keys)
    LOG_LEVEL: str = "INFO"
    DEVICE: str = "cuda"
    DATA_PATH: Path = Path("./data")
    MODELS_PATH: Path = Path("./models")

    # Trading Defaults
    TIMEFRAMES: List[str] = ["15m", "1h", "4h", "1d"]
    SYMBOLS: List[str] = [
        # Validated Kraken EUR pairs (49 pairs - verified 2026-01-05)
        "BTC/EUR", "ETH/EUR", "SOL/EUR", "XRP/EUR", "ADA/EUR",
        "DOGE/EUR", "AVAX/EUR", "LINK/EUR", "DOT/EUR", "DAI/EUR",
        "LTC/EUR", "ATOM/EUR", "UNI/EUR", "NEAR/EUR", "FIL/EUR",
        "APT/EUR", "ARB/EUR", "OP/EUR", "AAVE/EUR", "GRT/EUR",
        "ALGO/EUR", "XLM/EUR", "ETC/EUR", "XTZ/EUR", "SHIB/EUR",
        "BCH/EUR", "TRX/EUR", "VET/EUR", "SAND/EUR", "MANA/EUR",
        "CHZ/EUR", "FLOW/EUR", "FET/EUR", "RUNE/EUR", "INJ/EUR",
        "SUI/EUR", "RENDER/EUR", "IMX/EUR", "HBAR/EUR", "STX/EUR",
        "PEPE/EUR", "WIF/EUR", "BONK/EUR", "KAVA/EUR", "AXS/EUR",
        "ICP/EUR", "TON/EUR", "POL/EUR", "BNB/EUR",
    ]
    
    # === OPTIMIZED TRADING PARAMETERS ===
    # Position Sizing
    MAX_POSITION_PERCENT: float = 0.10       # Max 10% per position (reduced for more positions)
    MIN_TRADE_VALUE: float = 50.0            # Minimum $50 per trade (lower for more trades)
    RISK_PER_TRADE: float = 0.015            # Risk 1.5% per trade (conservative)
    
    # Risk Management
    DEFAULT_STOP_LOSS: float = 0.025         # 2.5% stop loss
    DEFAULT_TAKE_PROFIT: float = 0.045       # 4.5% take profit (base, dynamic in code)
    MAX_DAILY_TRADES: int = 9999             # Effectively unlimited
    COOLDOWN_MINUTES: int = 5                # Aggressive: reduced cooldown for faster re-entry
    MAX_OPEN_POSITIONS: int = 30             # Max concurrent positions (paper trading)
    MAX_OPEN_POSITIONS_LIVE: int = 15         # Safety limit for live trading
    MAX_DAILY_LOSS: float = 0.05             # Stop trading at -5% daily
    MAX_TOTAL_EXPOSURE: float = 0.70         # Max 70% of capital exposed
    
    # Dynamic Take-Profit / Trailing Stop
    TRAILING_STOP_ACTIVATION: float = 0.02  # Activate trailing at +2% profit
    TRAILING_STOP_DISTANCE: float = 0.01    # Trail 1% behind peak
    DYNAMIC_TP_LOW_VOL: float = 0.03        # TP for low volatility (3%)
    DYNAMIC_TP_NORMAL: float = 0.045        # TP for normal volatility (4.5%)
    DYNAMIC_TP_HIGH_VOL: float = 0.06       # TP for high volatility (6%)
    
    # Signal Thresholds (AGGRESSIVE MODE)
    MIN_SIGNAL_CONFIDENCE: float = 0.20      # Lowered for more signals
    STRONG_SIGNAL_THRESHOLD: float = 0.70    # Strong signal threshold
    
    # Confidence-based position sizing multipliers
    CONFIDENCE_MULTIPLIER_LOW: float = 0.5   # 50-60% confidence
    CONFIDENCE_MULTIPLIER_MEDIUM: float = 0.8  # 60-70% confidence
    CONFIDENCE_MULTIPLIER_HIGH: float = 1.0  # 70-85% confidence
    CONFIDENCE_MULTIPLIER_VERY_HIGH: float = 1.2  # >85% confidence
    
    # Trading Fees
    MAKER_FEE: float = 0.001                 # 0.1% maker fee
    TAKER_FEE: float = 0.001                 # 0.1% taker fee
    
    # Cycle Timing (AGGRESSIVE MODE)
    TRADING_CYCLE_SECONDS: int = 30          # Fast cycles for quick reaction
    DATA_FETCH_LIMIT: int = 200              # Candles to fetch

    class Config:
        env_file = ".env"

settings = Settings()

