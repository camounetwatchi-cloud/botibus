import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.data.storage import DataStorage

def verify_dashboard_compatibility():
    print("Testing Dashboard Logic Compatibility...")
    
    storage = DataStorage(read_only=True)
    
    # 1. Test Bot Status Logic
    print("\n[1] Testing Bot Status Logic...")
    bot_status = storage.get_bot_status()
    print(f"Bot Status Data: {bot_status}")
    
    last_heartbeat = bot_status.get("last_heartbeat")
    if last_heartbeat:
        print(f"Heartbeat type: {type(last_heartbeat)}")
        
        # Simulate Dashboard Logic
        try:
            if isinstance(last_heartbeat, str):
                last_heartbeat = pd.to_datetime(last_heartbeat)
            
            # This is the line from dashboard.py
            time_since = datetime.now() - last_heartbeat.replace(tzinfo=None)
            
            print(f"Time since heartbeat: {time_since}")
            if time_since < timedelta(minutes=20):
                print("SUCCESS: Heartbeat is considered ACTIVE")
            else:
                print("WARNING: Heartbeat is OLD (expected if bot stopped)")
                
        except Exception as e:
            print(f"FAILED: Dashboard heartbeat logic crashed: {e}")
            return False
    else:
        print("WARNING: No heartbeat found (bot never ran?)")

    # 2. Test Trades Data
    print("\n[2] Testing Trades Data...")
    open_trades = storage.get_trades(status="open")
    closed_trades = storage.get_trades(status="closed")
    
    print(f"Open Trades: {len(open_trades)}")
    print(f"Closed Trades: {len(closed_trades)}")
    
    if not open_trades.empty:
        # Check required columns for dashboard
        required_cols = ['symbol', 'side', 'entry_price', 'amount', 'entry_time']
        missing = [col for col in required_cols if col not in open_trades.columns]
        if missing:
            print(f"FAILED: Missing columns for Open Trades: {missing}")
            return False
            
        # Test formatting logic
        try:
            disp_trades = open_trades.copy()
            disp_trades['Entry Time'] = pd.to_datetime(disp_trades['entry_time']).dt.strftime('%H:%M:%S')
            print("SUCCESS: Open trades formatting works")
        except Exception as e:
            print(f"FAILED: Open trades formatting error: {e}")
            return False

    if not closed_trades.empty:
        try:
            total_pnl = closed_trades['pnl'].sum()
            print(f"SUCCESS: PnL calculation works. Total: {total_pnl}")
        except Exception as e:
            print(f"FAILED: PnL calculation error: {e}")
            return False
            
    # 3. Test Balance
    print("\n[3] Testing Balance...")
    balance = storage.get_latest_balance()
    print(f"Balance: {balance}")
    if 'total' in balance and 'free' in balance:
        print("SUCCESS: Balance structure correct")
    else:
        print("FAILED: Invalid balance structure")
        return False

    print("\nOVERALL: Dashboard Compatibility Verified ✅")
    return True

if __name__ == "__main__":
    verify_dashboard_compatibility()
