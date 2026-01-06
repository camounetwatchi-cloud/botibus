import json
import sys
sys.path.insert(0, '.')
from src.data.storage import DataStorage

storage = DataStorage(read_only=True)

# Check balance more deeply
print("=== BALANCE ANALYSIS ===")
balance = storage.get_latest_balance()
print(f"Latest Balance: {balance}")

# Query balance table directly
bh = storage.get_balance_history(hours=168)  # last 7 days
print(f"Balance history rows (7 days): {len(bh)}")
if len(bh) > 0:
    print(f"First: {bh.iloc[0].to_dict()}")
    print(f"Last: {bh.iloc[-1].to_dict()}")

# Check trades
print("\n=== TRADES ANALYSIS ===")
all_trades = storage.get_trades(status=None)
print(f"Total trades: {len(all_trades)}")
if not all_trades.empty:
    print(f"Columns: {list(all_trades.columns)}")
    print(f"Statuses: {all_trades['status'].value_counts().to_dict()}")
    print("\nSample trades:")
    for i, (_, row) in enumerate(all_trades.head(3).iterrows()):
        print(f"  Trade {i+1}: symbol={row.get('symbol')}, side={row.get('side')}, status={row.get('status')}, pnl={row.get('pnl')}, exit_price={row.get('exit_price')}, exit_time={row.get('exit_time')}")

# Check for trades that might be incorrectly marked
open_trades = storage.get_trades(status='open')
print(f"\nOpen trades with PnL calculated: {len(open_trades[open_trades['pnl'].notna()]) if not open_trades.empty and 'pnl' in open_trades.columns else 0}")

# What should be closed?
if not all_trades.empty:
    has_exit = all_trades['exit_time'].notna()
    has_exit_price = all_trades['exit_price'].notna()
    print(f"\nTrades with exit_time: {has_exit.sum()}")
    print(f"Trades with exit_price: {has_exit_price.sum()}")
    incomplete = all_trades[(has_exit | has_exit_price) & (all_trades['status'] == 'open')]
    if len(incomplete) > 0:
        print(f"\n!!! ISSUE: {len(incomplete)} trades have exit data but status='open' !!!")

print("\nAnalysis complete!")
