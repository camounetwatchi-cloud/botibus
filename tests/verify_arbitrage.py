
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
from dataclasses import dataclass

# Mock infrastructure
sys.modules['src.data.storage'] = MagicMock()
sys.modules['src.data.collector'] = MagicMock()
sys.modules['src.features.technical'] = MagicMock()
sys.modules['src.ml.signal_generator'] = MagicMock()
sys.modules['loguru'] = MagicMock()

# Setup settings mock specifically with ALL int values
settings_mock = MagicMock()
settings_mock.MIN_TRADE_VALUE = 10.0
settings_mock.MAX_OPEN_POSITIONS = 10
settings_mock.MAX_DAILY_TRADES = 100
settings_mock.MAX_DAILY_LOSS = 0.05
settings_mock.COOLDOWN_MINUTES = 0
settings_mock.DEFAULT_STOP_LOSS = 0.025
settings_mock.DEFAULT_TAKE_PROFIT = 0.045
settings_mock.MAX_POSITION_PERCENT = 0.15
settings_mock.RISK_PER_TRADE = 0.02
settings_mock.TRAILING_STOP_ACTIVATION = 0.03
settings_mock.TRAILING_STOP_DISTANCE = 0.015
settings_mock.DYNAMIC_TP_LOW_VOL = 0.03
settings_mock.DYNAMIC_TP_NORMAL = 0.045
settings_mock.DYNAMIC_TP_HIGH_VOL = 0.06
settings_mock.MAX_TOTAL_EXPOSURE = 2.0
settings_mock.MIN_SIGNAL_CONFIDENCE = 0.55
settings_mock.STRONG_SIGNAL_THRESHOLD = 0.70
settings_mock.CONFIDENCE_MULTIPLIER_LOW = 0.5
settings_mock.CONFIDENCE_MULTIPLIER_MEDIUM = 0.8
settings_mock.CONFIDENCE_MULTIPLIER_HIGH = 1.0
settings_mock.CONFIDENCE_MULTIPLIER_VERY_HIGH = 1.2
settings_mock.ACTIVE_EXCHANGE = "mock_exchange"
settings_mock.BINANCE_API_KEY = "mock"
settings_mock.BINANCE_SECRET_KEY = "mock"
settings_mock.BYBIT_API_KEY = "mock"
settings_mock.BYBIT_SECRET_KEY = "mock"
settings_mock.KRAKEN_API_KEY = "mock"
settings_mock.KRAKEN_SECRET_KEY = "mock"
settings_mock.PAPER_TRADING = True
settings_mock.MAX_OPEN_POSITIONS_LIVE = 10
settings_mock.SYMBOLS = ["WEAK_COIN", "STRONG_COIN"]
settings_mock.TRADING_CYCLE_SECONDS = 10

sys.modules['src.config.settings'] = MagicMock()
sys.modules['src.config.settings'].settings = settings_mock

# Import the class to test
project_root = Path('.').resolve()
sys.path.append(str(project_root))

from scripts.live_trade import OptimizedTradingBot
from src.trading.risk_manager import RiskManager

@dataclass
class MockSignal:
    signal: MagicMock
    confidence: float
    action: str
    is_actionable: bool = True
    atr: float = 0.0
    technical_score: float = 0.0
    ml_score: float = 0.0
    volume_score: float = 0.0
    reasons: list = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

async def test_arbitrage():
    print("Testing Arbitrage Logic...")
    
    try:
        # 1. Setup Bot
        bot = OptimizedTradingBot()
        
        # Override Internals
        bot.storage = MagicMock()
        bot.collector = MagicMock()
        bot.signal_generator = MagicMock()
        
        # Override Risk Manager instance to control it completely
        # Note: OptimizedTradingBot creates a real RiskManager because we didn't mock the class def
        # So we overwrite the instance
        bot.risk_manager = MagicMock()
        bot.risk_manager.get_risk_summary.return_value = {'can_trade': True, 'daily_trades': 0}
        bot.risk_manager.can_trade.side_effect = lambda sym, bal: (True, "OK") # Allowed generally
        
        # Mock methods that would trigger external calls
        bot.check_open_positions = AsyncMock()
        bot.execute_signal = AsyncMock()
        bot.close_position = AsyncMock()
        
        # 2. Setup Scenario
        bot.total_balance = 1000.0
        bot.free_balance = 10.0   # Low funds
        
        # Signals
        weak_signal = MockSignal(MagicMock(), 0.45, "BUY") # Confidence 0.45
        weak_signal.signal.name = "BUY"
        strong_signal = MockSignal(MagicMock(), 0.85, "BUY") # Confidence 0.85
        strong_signal.signal.name = "STRONG_BUY"
        
        async def mock_analyze(symbol):
            if symbol == "WEAK_COIN":
                return (100.0, weak_signal)
            elif symbol == "STRONG_COIN":
                return (100.0, strong_signal)
            return (100.0, None)
        
        bot.fetch_and_analyze = mock_analyze
        
        # Initial State: Holding WEAK_COIN
        bot.symbols = ["WEAK_COIN", "STRONG_COIN"]
        bot.open_positions = {
            "trade_1": {
                "symbol": "WEAK_COIN",
                "entry_price": 100.0,
                "amount": 1.0,
                "side": "buy",
                "entry_time": "mock_time"
            }
        }
        
        # Mock calculate_position_size
        # Must handle the "Insufficient Funds" case
        # live_trade code: pos_size, _, _ = calculate(...)
        # then: cost = pos_size * price
        # if can_trade_risk and cost > 0: ...
        
        def calc_size_side_effect(balance, price, confidence, atr=0):
            print(f"DEBUG: calculate_position_size called with bal={balance}")
            if balance < 100: 
                # Simulate not enough funds for min trade
                return 0.0, 0.0, 0.0
            return 1.0, 90.0, 110.0
            
        bot.risk_manager.calculate_position_size.side_effect = calc_size_side_effect
        
        # 3. Run Logic
        print("Running Cycle...")
        await bot.run_cycle()
        
        # 4. Verify Results
        print("\nVerifying...")
        
        # Verify Close WEAK_COIN
        if bot.close_position.called:
            args = bot.close_position.call_args[0]
            print(f"✅ Closed Position: {args[0]} (Reason: {args[2]})")
            assert args[2] == "ARBITRAGE_SWAP"
        else:
            print("❌ Did not close weak position")
            
        # Verify Open STRONG_COIN
        if bot.execute_signal.called:
            args = bot.execute_signal.call_args[0]
            print(f"✅ Opened Position: {args[0]}")
            assert args[0] == "STRONG_COIN"
        else:
            print("❌ Did not open strong position")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_arbitrage())
