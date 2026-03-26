import json
import re
from datetime import datetime, timezone

# Parse log for all successful scans
log_path = "/Users/sangho/클로드 코드/scanner/data/scan_daemon.log"
output_path = "/Users/sangho/클로드 코드/scanner/data/prebuilt-scans.json"

# Load existing results
with open(output_path) as f:
    existing = json.load(f)
existing_urls = {r["url"] for r in existing}

# Also load the original script results (first 9) - these are already in existing
# Now we need to check what's in the log but missing from the file

# Parse the daemon log to find all scan attempts and their results
# Format: "Scanning Name (url)..." followed by "Score: X, Rating: Y" 
with open(log_path) as f:
    log_lines = f.readlines()

missing_services = []
i = 0
while i < len(log_lines):
    line = log_lines[i].strip()
    m = re.match(r'\[.*?\] Scanning (.+?) \((.+?)\)\.\.\.$', line)
    if m:
        name = m.group(1)
        url = m.group(2)
        # Check next line for score
        if i+1 < len(log_lines):
            next_line = log_lines[i+1].strip()
            sm = re.match(r'\[.*?\]\s+(?:->|Retry OK\.)?\s*Score:\s*(\d+),\s*Rating:\s*(.+)$', next_line)
            if sm and url not in existing_urls:
                score = int(sm.group(1))
                rating = sm.group(2).strip()
                missing_services.append({
                    "url": url,
                    "service_name": name,
                    "clarvia_score": score,
                    "rating": rating,
                    "dimensions": None,
                    "scan_id": None,
                    "scanned_at": datetime.now(timezone.utc).isoformat()
                })
                existing_urls.add(url)
    i += 1

print(f"Found {len(missing_services)} missing services in log:")
for s in missing_services:
    print(f"  {s['clarvia_score']:3d} | {s['rating']:10s} | {s['service_name']}")

# Merge
all_results = existing + missing_services
all_results.sort(key=lambda x: (x.get("clarvia_score") or 0), reverse=True)

with open(output_path, "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\nTotal after merge: {len(all_results)}")
