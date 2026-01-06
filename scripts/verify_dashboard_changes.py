
import pandas as pd
import sys
import os

# Mock streamlit
class MockSt:
    def subheader(self, *args): pass
    def info(self, *args): pass
    def dataframe(self, *args, **kwargs): 
        print("Dataframe rendered with columns:", args[0].columns.tolist())
        if 'column_config' in kwargs:
            print("Column config present")
    class column_config:
        def NumberColumn(*args, **kwargs): return "NumberColumn"
        def TextColumn(*args, **kwargs): return "TextColumn"

sys.modules['streamlit'] = MockSt()

# Now we can import the dashboard functionality or just copy-paste the logic to test it
# But importing might trigger other things. Let's just test the logic snippet.

def test_logic():
    print("Testing active positions logic...")
    
    # Mock data
    live_prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0}
    
    open_trades_data = {
        'symbol': ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        'side': ["buy", "sell", "buy"],
        'entry_price': [48000.0, 3100.0, 100.0],
        'amount': [0.1, 1.0, 10.0],
        'entry_time': [pd.Timestamp.now(), pd.Timestamp.now(), pd.Timestamp.now()]
    }
    open_trades = pd.DataFrame(open_trades_data)
    
    # --- LOGIC FROM DASHBOARD ---
    if not open_trades.empty:
        disp_trades = open_trades.copy()
        
        current_prices = []
        current_values = []
        pnl_values = []
        
        for _, row in disp_trades.iterrows():
            c_price = live_prices.get(row['symbol'], row['entry_price'])
            
            c_val = c_price * row['amount']
            entry_val = row['entry_price'] * row['amount']
            
            if row['side'] == 'buy':
                pnl = c_val - entry_val
            else:
                pnl = entry_val - c_val
            
            current_prices.append(c_price)
            current_values.append(c_val)
            pnl_values.append(pnl)
        
        disp_trades['Current Price'] = current_prices
        disp_trades['Current Value'] = current_values
        disp_trades['Unrealized PnL'] = pnl_values
        disp_trades['Time'] = pd.to_datetime(disp_trades['entry_time']).dt.strftime('%H:%M:%S')
        
        show_cols = ['symbol', 'side', 'amount', 'entry_price', 'Current Price', 'Current Value', 'Unrealized PnL', 'Time']
        
        print("Resulting DataFrame Head:")
        print(disp_trades[show_cols])
        
        # Validation
        # BTC Buy: Entered 48000, Current 50000. Amount 0.1. PnL = (50000-48000)*0.1 = 200. Check.
        assert abs(disp_trades.iloc[0]['Unrealized PnL'] - 200.0) < 0.01
        
        # ETH Sell: Entered 3100, Current 3000. Amount 1.0. PnL = (3100-3000)*1.0 = 100. Check.
        assert abs(disp_trades.iloc[1]['Unrealized PnL'] - 100.0) < 0.01
        
        # SOL Buy: Entered 100, Current 100 (fallback). Amount 10. PnL = 0. Check.
        assert abs(disp_trades.iloc[2]['Unrealized PnL'] - 0.0) < 0.01
        
        print("\n✅ Logic verified successfully!")

if __name__ == "__main__":
    test_logic()
