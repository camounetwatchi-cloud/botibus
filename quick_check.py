"""Quick GH Actions check."""
import subprocess
import json

result = subprocess.run(
    ["gh", "run", "list", "--repo", "camounetwatchi-cloud/botibus", "--limit", "10", "--json", "conclusion,createdAt"],
    capture_output=True,
    text=True
)

runs = json.loads(result.stdout)
print("Last 10 workflow runs:")
for r in runs:
    s = r.get('conclusion', 'running')
    d = r.get('createdAt', '')[:16]
    print(f"  {d} -> {s}")
