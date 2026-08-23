"""
Analyze TheKnot state data structure
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# Load marketplace state
with open(out / 'initial_state.json') as f:
    state = json.load(f)

print("=== MARKETPLACE STATE ANALYSIS ===")

# VENDORS
vendors = state.get('vendors', {})
print(f"\n--- vendors ({len(vendors)} keys) ---")
for k, v in vendors.items():
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
        if v and isinstance(v[0], dict):
            print(f"    sample keys: {list(v[0].keys())}")
    elif isinstance(v, dict):
        print(f"  {k}: dict{{{', '.join(list(v.keys())[:8])}{'...' if len(v) > 8 else ''}}}")
    else:
        print(f"  {k}: {v}")

# Show a profile
profiles = vendors.get('profiles', [])
if profiles:
    p = profiles[0]
    print(f"\n--- Sample Vendor Profile ---")
    for k, vals in sorted(p.items()):
        if vals is not None and vals != '' and vals != [] and vals != {}:
            s = json.dumps(vals, default=str)
            print(f"  {k}: {s[:300]}")

# SEARCH
search = state.get('search', {})
print(f"\n--- search ---")
print(f"  totalResults: {search.get('totalResults')}")
print(f"  isFetching: {search.get('isFetching')}")
print(f"  pagination: {json.dumps(search.get('pagination', {}), default=str)[:300]}")

# PAGE
page = state.get('page', {})
print(f"\n--- page ---")
print(f"  keys: {list(page.keys())[:15]}")
print(f"  marketCode: {page.get('marketCode')}")
print(f"  category: {page.get('category')}")
print(f"  locationName: {page.get('locationName')}")

# CATEGORY
cat = state.get('category', {})
print(f"\n--- category ---")
if isinstance(cat, dict):
    for k, v in cat.items():
        s = json.dumps(v, default=str)
        if len(s) < 300:
            print(f"  {k}: {s}")

# VENDOR DETAIL
print("\n\n=== VENDOR DETAIL STATE ANALYSIS ===")
with open(out / 'vendor_detail_state.json') as f:
    detail = json.load(f)

vd = detail.get('vendor', {})
print(f"\n--- vendor ({len(vd)} keys) ---")
if isinstance(vd, dict):
    for k, v in sorted(vd.items()):
        if v is not None and v != '' and v != [] and v != {}:
            s = json.dumps(v, default=str)
            print(f"  {k}: {s[:500]}")

print("\n--- End of Analysis ---")