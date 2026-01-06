import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.data.storage import DataStorage
import pandas as pd

storage = DataStorage()
trades = storage.get_trades()

# Filter for XRP/EUR and price close to 1.91578
xrp_trades = trades[trades['symbol'] == 'XRP/EUR']
print(f"Total XRP trades found: {len(xrp_trades)}")
print(xrp_trades.head(20).to_string())

# Search for the specific trade
match = xrp_trades[
    (xrp_trades['entry_price'].round(5) == 1.91578) | 
    (xrp_trades['exit_price'].round(5) == 1.91578)
]

if not match.empty:
    print("\n--- MATCHING TRADE ---")
    print(match.to_string())
else:
    print("\nNo exact price match found. Showing recent XRP trades:")
    print(xrp_trades.sort_values('entry_time', ascending=False).head(5).to_string())
