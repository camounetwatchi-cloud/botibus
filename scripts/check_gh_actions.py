"""Check GitHub Actions runs status - writes to file."""
import subprocess
import json
from pathlib import Path

result = subprocess.run(
    ["gh", "run", "list", "--repo", "camounetwatchi-cloud/botibus", "--limit", "30", "--json", "status,conclusion,createdAt,displayTitle,databaseId"],
    capture_output=True,
    text=True
)

runs = json.loads(result.stdout)

output_file = Path(__file__).parent.parent / "gh_actions_report.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("GITHUB ACTIONS WORKFLOW RUNS - camounetwatchi-cloud/botibus\n")
    f.write("=" * 80 + "\n\n")
    
    success_count = 0
    failure_count = 0
    
    for run in runs:
        status = run.get('conclusion') or run.get('status')
        created = run.get('createdAt', '')[:19].replace('T', ' ')
        title = run.get('displayTitle', '')[:50]
        run_id = run.get('databaseId')
        
        if status == "success":
            icon = "[OK]"
            success_count += 1
        elif status == "failure":
            icon = "[FAIL]"
            failure_count += 1
        else:
            icon = f"[{status}]"
        
        f.write(f"{icon:8} {created} | {title}\n")
    
    f.write("\n" + "=" * 80 + "\n")
    f.write(f"Total runs: {len(runs)} | Success: {success_count} | Failures: {failure_count}\n")
    f.write("=" * 80 + "\n")

print(f"Report written to {output_file}")
