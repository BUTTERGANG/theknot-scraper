"""
Deeper analysis of TheKnot state data
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# Find where the actual vendor listing data is
with open(out / 'initial_state.json') as f:
    state = json.load(f)

print("=== MARKETPLACE STATE - ALL NON-EMPTY SECTIONS ===")
for section, data in sorted(state.items()):
    if data is None or data == {} or data == []:
        continue
    
    if isinstance(data, dict):
        # Check if there are any populated fields beyond defaults
        non_default = {k: v for k, v in data.items() 
                      if v is not None and v != '' and v != [] and v != {} and v != False and v != 0}
        if non_default:
            print(f"\n--- {section} ({len(non_default)} populated keys) ---")
            for k, v in list(non_default.items())[:5]:
                s = json.dumps(v, default=str)
                print(f"  {k}: {s[:200]}")

# DIG INTO SEARCH
search = state.get('search', {})
print(f"\n\n=== SEARCH STATE FULL ===")
print(json.dumps(search, default=str)[:2000])

# Vendor detail analysis
print("\n\n=== VENDOR DETAIL RAW ===")
with open(out / 'vendor_detail_state.json') as f:
    detail = json.load(f)

vendor_raw = detail.get('vendor', {}).get('vendorRaw', {})
if vendor_raw:
    for k, v in sorted(vendor_raw.items()):
        if v is not None and v != '' and v != [] and v != {}:
            s = json.dumps(v, default=str)
            print(f"  {k}: {s[:500]}")

# Also check the full 'vendor' object
print("\n\n=== VENDOR OBJECT FULL ===")
v_obj = detail.get('vendor', {}).get('vendor', {})
if v_obj:
    for k, v in sorted(v_obj.items()):
        if v is not None and v != '' and v != [] and v != {}:
            s = json.dumps(v, default=str)
            print(f"  {k}: {s[:500]}")