"""Analyze GH Actions and bot status comprehensively."""
import subprocess
import json
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

output_file = Path(__file__).parent.parent / "diagnostic_report.txt"

with open(output_file, 'w', encoding='utf-8') as f:

    # Get GH runs info
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "camounetwatchi-cloud/botibus", "--limit", "30", "--json", "conclusion,createdAt,status"],
        capture_output=True,
        text=True
    )

    runs = json.loads(result.stdout)

    # Analysis
    f.write("\n" + "="*60 + "\n")
    f.write("COMPREHENSIVE BOT DIAGNOSTIC REPORT\n")
    f.write(f"Generated at: {datetime.now()}\n")
    f.write("="*60 + "\n")

    f.write("\n[1] GITHUB ACTIONS STATUS\n")
    f.write("-" * 40 + "\n")

    success_count = sum(1 for r in runs if r.get('conclusion') == 'success')
    failure_count = sum(1 for r in runs if r.get('conclusion') == 'failure')
    total = len(runs)

    f.write(f"Last {total} runs: {success_count} success, {failure_count} failures\n")

    if runs:
        latest = runs[0]
        latest_time = latest.get('createdAt', '')
        latest_status = latest.get('conclusion') or latest.get('status')
        f.write(f"Most recent run: {latest_time} -> {latest_status}\n")
        
    # Check gap between runs
    if len(runs) >= 2:
        times = [datetime.fromisoformat(r['createdAt'].replace('Z', '+00:00')) for r in runs[:10]]
        gaps = [(times[i] - times[i+1]).total_seconds() / 60 for i in range(len(times)-1)]
        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        f.write(f"Average gap between runs: {avg_gap:.1f} min\n")
        f.write(f"Max gap: {max_gap:.1f} min\n")
        if max_gap > 20:
            f.write("WARNING: Gap > 20 min detected - possible missed runs!\n")

    # Check bot status from database
    f.write("\n[2] DATABASE STATUS\n")
    f.write("-" * 40 + "\n")

    try:
        from src.data.storage import DataStorage
        s = DataStorage(read_only=True)
        
        status = s.get_bot_status()
        last_hb = status.get('last_heartbeat')
        f.write(f"Last heartbeat: {last_hb}\n")
        
        if last_hb:
            if hasattr(last_hb, 'replace'):
                last_hb = last_hb.replace(tzinfo=None)
            time_since = datetime.now() - last_hb
            f.write(f"Time since heartbeat: {time_since}\n")
            
            if time_since > timedelta(hours=1):
                f.write("CRITICAL: Bot hasn't updated status in over 1 hour!\n")
                f.write("This means GH Actions runs are NOT updating the database.\n")
        
        f.write(f"Open positions in DB: {status.get('open_positions')}\n")
        f.write(f"Exchange: {status.get('exchange')}\n")
        f.write(f"Mode: {status.get('mode')}\n")
        
        # Check if using PostgreSQL or DuckDB
        f.write(f"\nLocal script using PostgreSQL: {s.use_postgres}\n")
        
    except Exception as e:
        f.write(f"Error reading database: {e}\n")

    f.write("\n[3] DIAGNOSIS\n")
    f.write("-" * 40 + "\n")

    if success_count > 0 and runs:
        f.write("GitHub Actions IS running successfully.\n")
        f.write("But the database heartbeat is stale.\n")
        f.write("\nPossible causes:\n")
        f.write("1. GH Actions can't connect to Supabase (IPv6/IPv4 issue)\n")
        f.write("2. DATABASE_URL secret not configured in GitHub\n")
        f.write("3. Database writes failing silently in GH Actions\n")
        f.write("\nRecommended actions:\n")
        f.write("- Check GH Actions logs for database errors\n")
        f.write("- Verify DATABASE_URL secret is set correctly\n")
        f.write("- Check Supabase dashboard for connection issues\n")
    else:
        f.write("GitHub Actions may have issues - check workflow configuration\n")

    f.write("\n" + "="*60 + "\n")

print(f"Report written to {output_file}")
