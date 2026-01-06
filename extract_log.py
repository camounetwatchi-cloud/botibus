"""Extract key info from GH Actions log - write to file."""
from pathlib import Path

log_file = Path("gh_run_log.txt")
content = log_file.read_text(encoding='utf-8', errors='ignore')

output_file = Path("log_summary.txt")

lines = content.split('\n')

keywords = ['PostgreSQL', 'INFO', 'ERROR', 'WARNING', 'DuckDB', 'Supabase', 'heartbeat', 'Cycle', 'positions', 'Balance', 'BALANCE', 'Trade blocked', 'OPEN', 'signal']

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("KEY LOG ENTRIES FROM LATEST GH ACTIONS RUN\n")
    f.write("="*80 + "\n\n")
    
    for line in lines:
        for kw in keywords:
            if kw in line:
                # Clean the line
                clean = line.strip()
                if len(clean) > 10:
                    f.write(clean[:150] + "\n")
                break
    
    f.write("\n" + "="*80 + "\n")

print(f"Summary written to {output_file}")
