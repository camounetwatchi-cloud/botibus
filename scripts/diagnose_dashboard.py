#!/usr/bin/env python
"""Diagnostic script for Dashboard Data Issues"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

try:
    import duckdb
except ImportError:
    duckdb = None

from src.data.storage import DataStorage
from datetime import datetime, timedelta
import pandas as pd

def main():
    print("="*60)
    print("DASHBOARD DATA DIAGNOSTIC")
    print("="*60)
    
    storage = DataStorage(read_only=True)
    
    print(f"\n[1] Storage Backend: {storage.storage_type}")
    print(f"    PostgreSQL available: {storage._postgres_available}")
    print(f"    Connection error: {storage.connection_error}")
    
    print("\n[2] Balance Check:")
    balance = storage.get_latest_balance()
    print(f"    Latest balance: {balance}")
    
    print("\n[3] Balance History (for Equity Curve):")
    bh = storage.get_balance_history(hours=48)
    print(f"    Rows in last 48h: {len(bh)}")
    if not bh.empty:
        print(f"    First timestamp: {bh.iloc[0]['timestamp']}")
        print(f"    Last timestamp: {bh.iloc[-1]['timestamp']}")
        print(f"    Sample row: {bh.iloc[-1].to_dict()}")
    else:
        print("    *** NO BALANCE HISTORY - Equity curve will be flat ***")
    
    print("\n[4] Open Trades:")
    open_trades = storage.get_trades(status="open")
    print(f"    Count: {len(open_trades)}")
    if not open_trades.empty:
        print(f"    Columns: {list(open_trades.columns)}")
        print(f"    Sample: {open_trades.iloc[0].to_dict()}")
    
    print("\n[5] Closed Trades:")
    closed_trades = storage.get_trades(status="closed")
    print(f"    Count: {len(closed_trades)}")
    if not closed_trades.empty:
        print(f"    Columns: {list(closed_trades.columns)}")
        print(f"    Sample: {closed_trades.iloc[0].to_dict()}")
        pnl = closed_trades['pnl'].sum()
        print(f"    Total Realized PnL: ${pnl:.2f}")
    else:
        print("    *** NO CLOSED TRADES - Trade History will be empty ***")
    
    # Check for trades without status
    print("\n[6] All Trades (any status):")
    all_trades = storage.get_trades(status=None)
    print(f"    Total trades in DB: {len(all_trades)}")
    if not all_trades.empty:
        print(f"    Statuses found: {all_trades['status'].unique().tolist()}")
        
    print("\n[7] Bot Status:")
    bot_status = storage.get_bot_status()
    print(f"    Status: {bot_status}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    import json
    
    storage = DataStorage(read_only=True)
    
    open_trades = storage.get_trades(status="open")
    closed_trades = storage.get_trades(status="closed")
    all_trades = storage.get_trades(status=None)
    bh = storage.get_balance_history(hours=48)
    balance = storage.get_latest_balance()
    bot_status = storage.get_bot_status()
    
    result = {
        "storage_type": storage.storage_type,
        "postgres_available": storage._postgres_available,
        "connection_error": storage.connection_error,
        "balance": balance,
        "balance_history_count": len(bh),
        "balance_history_sample": bh.tail(3).to_dict(orient="records") if not bh.empty else [],
        "open_trades_count": len(open_trades),
        "open_trades_columns": list(open_trades.columns) if not open_trades.empty else [],
        "closed_trades_count": len(closed_trades),
        "closed_trades_columns": list(closed_trades.columns) if not closed_trades.empty else [],
        "all_trades_count": len(all_trades),
        "all_trades_statuses": all_trades['status'].unique().tolist() if not all_trades.empty else [],
        "bot_status": bot_status,
    }
    
    # Save to JSON file
    with open("diagnose_result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print("Results saved to diagnose_result.json")
    main()
