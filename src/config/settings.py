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
        # Top 10 cryptos by market cap (Kraken EUR pairs) - Optimized for speed
        "BTC/EUR",   # Bitcoin
        "ETH/EUR",   # Ethereum
        "SOL/EUR",   # Solana
        "XRP/EUR",   # Ripple
        "BNB/EUR",   # Binance Coin
        "ADA/EUR",   # Cardano
        "DOGE/EUR",  # Dogecoin
        "AVAX/EUR",  # Avalanche
        "LINK/EUR",  # Chainlink
        "DOT/EUR",   # Polkadot
    ]
    
    # === OPTIMIZED TRADING PARAMETERS ===
    # Position Sizing
    MAX_POSITION_PERCENT: float = 0.10       # Max 10% per position (reduced for more positions)
    MIN_TRADE_VALUE: float = 10.0            # Minimum 10€ per trade (allows small positions)
    RISK_PER_TRADE: float = 0.015            # Risk 1.5% per trade (conservative)
    
    # Risk Management
    DEFAULT_STOP_LOSS: float = 0.02          # 2% stop loss (tighter for better R:R)
    DEFAULT_TAKE_PROFIT: float = 0.05        # 5% take profit (1:2.5 R:R ratio)
    MAX_DAILY_TRADES: int = 9999             # Effectively unlimited
    COOLDOWN_MINUTES: int = 1                # Ultra-aggressive: minimal cooldown for fastest re-entry
    MAX_OPEN_POSITIONS: int = 30             # Max concurrent positions (paper trading)
    MAX_OPEN_POSITIONS_LIVE: int = 15         # Safety limit for live trading
    MAX_DAILY_LOSS: float = 0.05             # Stop trading at -5% daily
    MAX_TOTAL_EXPOSURE: float = 0.95         # Max 95% of capital exposed (aggressive, 5% buffer for fees)
    
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
    CONFIDENCE_MULTIPLIER_LOW: float = 0.3   # 50-60% confidence (reduced for weak signals)
    CONFIDENCE_MULTIPLIER_MEDIUM: float = 0.7  # 60-70% confidence
    CONFIDENCE_MULTIPLIER_HIGH: float = 1.0  # 70-85% confidence
    CONFIDENCE_MULTIPLIER_VERY_HIGH: float = 1.2  # >85% confidence
    
    # Simulated Slippage (Paper Trading Realism)
    SLIPPAGE_PERCENT: float = 0.0005         # 0.05% per execution (realistic market impact)
    
    # Trading Fees
    MAKER_FEE: float = 0.001                 # 0.1% maker fee
    TAKER_FEE: float = 0.001                 # 0.1% taker fee
    
    # Kraken Margin Trading Fees (realistic)
    MARGIN_OPENING_FEE: float = 0.0002       # 0.02% margin opening fee
    MARGIN_ROLLOVER_FEE: float = 0.0002      # 0.02% rollover fee (per 4 hours)
    ROLLOVER_INTERVAL_HOURS: int = 4         # Kraken charges every 4 hours
    
    # Kelly Criterion Settings (Intelligent Position Sizing)
    USE_KELLY_SIZING: bool = True            # Enable Kelly-based sizing
    KELLY_FRACTION_CAP: float = 0.25         # Max 25% per position
    KELLY_LOOKBACK_TRADES: int = 50          # Trades to analyze for Kelly
    
    # Market Regime Detection
    ADX_TREND_THRESHOLD: float = 25.0        # ADX > 25 = trending market
    
    # Cycle Timing (AGGRESSIVE MODE)
    TRADING_CYCLE_SECONDS: int = 15          # Fast cycles for quick reaction
    DATA_FETCH_LIMIT: int = 200              # Candles to fetch

    class Config:
        env_file = ".env"

settings = Settings()

