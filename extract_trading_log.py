"""Extract the trading cycle output from GH Actions log."""
from pathlib import Path

log_file = Path("gh_run_log.txt")
content = log_file.read_text(encoding='utf-8', errors='ignore')

# Find the "Run Trading Cycle" section
lines = content.split('\n')

in_trading_section = False
trading_lines = []

for line in lines:
    if "Run Trading Cycle" in line or "🚀 Run Trading" in line:
        in_trading_section = True
    if in_trading_section:
        trading_lines.append(line.strip())
    if "Cleaning up" in line and in_trading_section:
        break

output_file = Path("trading_cycle_log.txt")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(trading_lines))

print(f"Found {len(trading_lines)} lines in trading cycle section")
print(f"Written to {output_file}")

# Print last 30 lines
print("\nLast 30 lines of trading cycle:")
for line in trading_lines[-30:]:
    if len(line) > 5:
        print(line[:150])
