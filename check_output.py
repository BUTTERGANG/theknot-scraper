"""
Check output quality of the scraper
"""
import json
from pathlib import Path

output = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

with open(output / 'vendors_wedding-photographers_indianapolis_20260823_225609.json') as f:
    data = json.load(f)

print(f"DETAILED VENDORS ({len(data)} vendors)\n")

for i, v in enumerate(data, 1):
    print(f"--- Vendor {i}: {v.get('name')} ---")
    for k, val in sorted(v.items()):
        if val and val != [] and val != {} and val != 0 and val != '':
            s = json.dumps(val, default=str)
            if len(s) > 300:
                s = s[:300] + '...'
            print(f"  {k}: {s}")
    print()

print("=== RAW STATE FILES ===")
for f in sorted(output.glob('raw_*.json')):
    stat = f.stat()
    print(f"  {f.name}: {stat.st_size:,} bytes")