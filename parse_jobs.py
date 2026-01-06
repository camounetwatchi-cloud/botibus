"""Parse jobs.json to see step status."""
import json
from pathlib import Path

jobs_file = Path("jobs.json")
data = json.loads(jobs_file.read_text())

print("="*60)
print("GITHUB ACTIONS JOB STEPS STATUS")
print("="*60)

for job in data.get('jobs', []):
    print(f"\nJob: {job['name']} - Status: {job['conclusion']}")
    print("-"*40)
    for step in job.get('steps', []):
        name = step['name']
        conclusion = step.get('conclusion', 'running')
        status_icon = "✓" if conclusion == "success" else "✗" if conclusion == "failure" else "?"
        print(f"  {status_icon} {name}: {conclusion}")

print("\n" + "="*60)
