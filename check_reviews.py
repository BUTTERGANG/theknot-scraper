"""
Investigate what review data exists in TheKnot Redux state
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')
files = sorted(out.glob('raw_*.json'))

if not files:
    print("No raw state files found")
    exit()

with open(files[0]) as f:
    data = json.load(f)

v = data.get('vendor', {})
vendor_raw = v.get('vendorRaw', {}) or {}
vendor_obj = v.get('vendor', {}) or {}

print("=== REVIEW FIELDS IN VENDOR STATE ===\n")

# vendorRaw review fields
print("--- vendorRaw ---")
for k in sorted(vendor_raw.keys()):
    if 'review' in k.lower():
        val = json.dumps(vendor_raw[k], default=str)
        print(f"  {k}: {val[:400]}")

print("\n--- vendor object ---")
for k in sorted(vendor_obj.keys()):
    if 'review' in k.lower():
        val = json.dumps(vendor_obj[k], default=str)
        print(f"  {k}: {val[:400]}")

# Deep search for any review arrays
print("\n=== DEEP SEARCH FOR REVIEW TEXT ===\n")

def deep_search(obj, path="", depth=0):
    if depth > 6:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if 'review' in k.lower() and isinstance(v, (list, dict)):
                s = json.dumps(v, default=str)
                print(f"  {path}.{k} = {type(v).__name__} ({len(s)} chars)")
                if isinstance(v, list) and len(v) > 0:
                    first = v[0] if v else {}
                    print(f"    [0] keys: {list(first.keys()) if isinstance(first, dict) else type(first).__name__}")
                    print(f"    [0] preview: {json.dumps(first, default=str)[:300]}")
            deep_search(v, f"{path}.{k}", depth + 1)
    elif isinstance(obj, list) and len(obj) > 0:
        if isinstance(obj[0], dict):
            deep_search(obj[0], f"{path}[0]", depth + 1)

deep_search(data)

print("\n=== ALL KEYS IN VENDOR STATE ===\n")
print(f"vendorRaw top keys: {list(vendor_raw.keys())}")
print(f"vendor top keys: {list(vendor_obj.keys())}")

# Zola review data
print("\n=== ZOLA REVIEW DATA ===\n")
zola_files = sorted(out.glob('zola_vendor_detail_*.json') or out.glob('zola_next_data.json'))
if zola_files:
    with open(zola_files[-1]) as f:
        zola_data = json.load(f)
    
    storefront = zola_data.get('props', {}).get('pageProps', {}).get('storefront', {})
    if 'reviewCount' in storefront or 'averageReviewsRate' in storefront:
        print(f"  reviewCount: {storefront.get('reviewCount')}")
        print(f"  averageReviewsRate: {storefront.get('averageReviewsRate')}")
    
    # Search for review text
    def z_search(obj, path="", depth=0):
        if depth > 5: return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if 'review' in k.lower() and isinstance(v, (list, dict)):
                    s = json.dumps(v, default=str)
                    print(f"  {path}.{k} = {type(v).__name__} ({len(s)} chars)")
                    if isinstance(v, list) and len(v) > 0:
                        print(f"    [0]: {json.dumps(v[0], default=str)[:300]}")
                z_search(v, f"{path}.{k}", depth + 1)
    
    z_search(zola_data)

print("\n✅ Done")