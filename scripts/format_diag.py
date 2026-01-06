import json
d = json.load(open('diagnose_result.json'))

# Write a formatted report
with open('diag_report.txt', 'w', encoding='utf-8') as f:
    f.write("DASHBOARD DIAGNOSTIC REPORT\n")
    f.write("="*50 + "\n\n")
    f.write(f"Storage Type: {d['storage_type']}\n")
    f.write(f"PostgreSQL Available: {d['postgres_available']}\n")
    f.write(f"Connection Error: {d['connection_error']}\n\n")
    
    f.write(f"BALANCE:\n")
    f.write(f"  Total: {d['balance'].get('total')}\n")
    f.write(f"  Free: {d['balance'].get('free')}\n")
    f.write(f"  Used: {d['balance'].get('used')}\n\n")
    
    f.write(f"BALANCE HISTORY (Equity Curve):\n")
    f.write(f"  Rows in last 48h: {d['balance_history_count']}\n")
    if d['balance_history_sample']:
        f.write(f"  Sample rows:\n")
        for row in d['balance_history_sample']:
            f.write(f"    {row}\n")
    f.write("\n")
    
    f.write(f"TRADES:\n")
    f.write(f"  Open Trades: {d['open_trades_count']}\n")
    f.write(f"  Closed Trades: {d['closed_trades_count']}\n")
    f.write(f"  All Trades: {d['all_trades_count']}\n")
    f.write(f"  Trade Statuses: {d['all_trades_statuses']}\n")
    f.write(f"  Open Trade Columns: {d.get('open_trades_columns')}\n")
    f.write(f"  Closed Trade Columns: {d.get('closed_trades_columns')}\n\n")
    
    f.write(f"BOT STATUS:\n")
    for k, v in d['bot_status'].items():
        f.write(f"  {k}: {v}\n")

print("Report written to diag_report.txt")
