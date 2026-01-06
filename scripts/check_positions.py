"""Check open positions against current prices - write to file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.data.storage import DataStorage
from src.data.collector import DataCollector

async def check_positions():
    storage = DataStorage(read_only=True)
    collector = DataCollector()
    
    open_trades = storage.get_trades(status='open')
    
    output_file = Path(__file__).parent.parent / "positions_analysis.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        if open_trades.empty:
            f.write("No open positions found in database.\n")
            return
        
        f.write("=" * 80 + "\n")
        f.write("OPEN POSITIONS ANALYSIS\n")
        f.write("=" * 80 + "\n")
        
        total_pnl = 0.0
        total_value = 0.0
        stop_loss_hit = []
        take_profit_hit = []
        
        for _, trade in open_trades.iterrows():
            symbol = trade['symbol']
            entry_price = float(trade['entry_price'])
            amount = float(trade['amount'])
            side = trade['side']
            entry_time = trade['entry_time']
            
            # Get current price
            try:
                df = await collector.fetch_ohlcv(symbol, "1h", limit=1)
                if df.empty:
                    f.write(f"  {symbol}: Could not fetch current price\n")
                    continue
                current_price = float(df.iloc[-1]['close'])
            except Exception as e:
                f.write(f"  {symbol}: Error fetching price - {e}\n")
                continue
            
            # Calculate P&L
            position_value = entry_price * amount
            if side == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price * 100
                pnl_usd = (current_price - entry_price) * amount
            else:  # sell/short
                pnl_pct = (entry_price - current_price) / entry_price * 100
                pnl_usd = (entry_price - current_price) * amount
            
            total_pnl += pnl_usd
            total_value += position_value
            
            # Determine status
            if pnl_pct <= -2.5:
                status = "[STOP LOSS HIT]"
                stop_loss_hit.append((symbol, pnl_pct, pnl_usd))
            elif pnl_pct >= 4.5:
                status = "[TAKE PROFIT HIT]"
                take_profit_hit.append((symbol, pnl_pct, pnl_usd))
            elif pnl_pct > 0:
                status = "[In Profit]"
            else:
                status = "[In Loss]"
            
            f.write(f"\n{symbol} ({side.upper()})\n")
            f.write(f"  Entry: ${entry_price:.4f} @ {entry_time}\n")
            f.write(f"  Current: ${current_price:.4f}\n")
            f.write(f"  P&L: {pnl_pct:+.2f}% (${pnl_usd:+.2f})\n")
            f.write(f"  Status: {status}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"TOTAL UNREALIZED P&L: ${total_pnl:+.2f}\n")
        f.write(f"Total Position Value: ${total_value:.2f}\n")
        
        if stop_loss_hit:
            f.write(f"\n[!] POSITIONS THAT HIT STOP LOSS (-2.5%):\n")
            for sym, pct, usd in stop_loss_hit:
                f.write(f"    {sym}: {pct:+.2f}% (${usd:+.2f})\n")
        
        if take_profit_hit:
            f.write(f"\n[+] POSITIONS THAT HIT TAKE PROFIT (+4.5%):\n")
            for sym, pct, usd in take_profit_hit:
                f.write(f"    {sym}: {pct:+.2f}% (${usd:+.2f})\n")
        
        f.write("=" * 80 + "\n")
    
    await collector.close()
    print(f"Report written to {output_file}")

if __name__ == "__main__":
    asyncio.run(check_positions())
