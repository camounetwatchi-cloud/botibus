"""Script to check bot status and trades - outputs to file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.storage import DataStorage
from datetime import datetime

output_file = Path(__file__).parent.parent / "status_report.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    s = DataStorage(read_only=True)

    f.write("=" * 60 + "\n")
    f.write("BOT STATUS CHECK\n")
    f.write("=" * 60 + "\n")

    status = s.get_bot_status()
    f.write(f"\n[Bot Status]\n")
    f.write(f"  Status: {status.get('status')}\n")
    f.write(f"  Last heartbeat: {status.get('last_heartbeat')}\n")
    f.write(f"  Open positions: {status.get('open_positions')}\n")
    f.write(f"  Exchange: {status.get('exchange')}\n")
    f.write(f"  Mode: {status.get('mode')}\n")

    # Calculate time since last heartbeat
    if status.get('last_heartbeat'):
        hb = status['last_heartbeat']
        if hasattr(hb, 'replace'):
            hb = hb.replace(tzinfo=None)
        time_since = datetime.now() - hb
        f.write(f"  Time since last heartbeat: {time_since}\n")

    balance = s.get_latest_balance()
    f.write(f"\n[Balance]\n")
    f.write(f"  Total: ${balance.get('total', 0):.2f}\n")
    f.write(f"  Free: ${balance.get('free', 0):.2f}\n")
    f.write(f"  Used: ${balance.get('used', 0):.2f}\n")

    trades = s.get_trades()
    open_trades = s.get_trades(status='open')
    closed_trades = s.get_trades(status='closed')

    f.write(f"\n[Trades Summary]\n")
    f.write(f"  Total trades: {len(trades)}\n")
    f.write(f"  Open trades: {len(open_trades)}\n")
    f.write(f"  Closed trades: {len(closed_trades)}\n")

    if not open_trades.empty:
        f.write(f"\n[Open Positions]\n")
        for _, t in open_trades.iterrows():
            f.write(f"  - {t['symbol']}: {t['side'].upper()} @ ${t['entry_price']:.2f} (qty: {t['amount']:.6f})\n")
            f.write(f"    Entry time: {t['entry_time']}\n")

    # Check recent trades
    if not trades.empty:
        f.write(f"\n[All Trades]\n")
        for _, t in trades.iterrows():
            pnl_str = f"PnL: ${t.get('pnl', 0):.2f}" if t.get('pnl') else ""
            f.write(f"  - {t['symbol']}: {t['side'].upper()} @ ${t['entry_price']:.2f} | Status: {t['status']} {pnl_str}\n")
            f.write(f"    Entry: {t['entry_time']}\n")

    f.write("\n" + "=" * 60 + "\n")

print(f"Report written to {output_file}")
