"""
Check all scraper outputs
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# List all output files
files = sorted(out.glob('*.json'))
print("=== OUTPUT FILES ===")
for f in files:
    sz = f.stat().st_size
    print(f"  {f.name}: {sz:,} bytes")

# WeddingWire
ww = sorted(out.glob('ww_*.json'))
if ww:
    with open(ww[-1]) as f:
        data = json.load(f)
    print(f"\n=== WEDDINGWIRE ({len(data)} vendors) ===")
    if data:
        v = data[0]
        print(f"Sample vendor keys: {list(v.keys())}")
        for k, val in sorted(v.items()):
            if val:
                s = json.dumps(val, default=str)[:200]
                print(f"  {k}: {s}")
        # Stats
        stats = {
            'name': sum(1 for v in data if v.get('name')),
            'rating': sum(1 for v in data if v.get('rating')),
            'price': sum(1 for v in data if v.get('starting_price')),
            'biz_url': sum(1 for v in data if v.get('biz_url')),
        }
        for k, cnt in stats.items():
            print(f"  {k}: {cnt}/{len(data)}")

# Zola
zl = sorted(out.glob('zola_*.json'))
if zl:
    with open(zl[-1]) as f:
        data = json.load(f)
    print(f"\n=== ZOLA ({len(data)} vendors) ===")
    if data:
        v = data[0]
        for k, val in sorted(v.items()):
            if val:
                s = json.dumps(val, default=str)[:200]
                print(f"  {k}: {s}")
        stats = {
            'name': sum(1 for v in data if v.get('name')),
            'rating': sum(1 for v in data if v.get('star_rating')),
            'price': sum(1 for v in data if v.get('starting_price')),
            'slug': sum(1 for v in data if v.get('slug')),
            'city': sum(1 for v in data if v.get('city')),
        }
        for k, cnt in stats.items():
            print(f"  {k}: {cnt}/{len(data)}")

# TheKnot
tk = sorted(out.glob('vendors_*.json'))
if tk:
    with open(tk[-1]) as f:
        data = json.load(f)
    print(f"\n=== THEKNOT ({len(data)} vendors) ===")
    if data:
        v = data[0]
        for k, val in sorted(v.items()):
            if val:
                s = json.dumps(val, default=str)[:200]
                print(f"  {k}: {s}")
        stats = {
            'name': sum(1 for v in data if v.get('name')),
            'phone': sum(1 for v in data if v.get('phone')),
            'email': sum(1 for v in data if v.get('email')),
            'rating': sum(1 for v in data if v.get('star_rating')),
            'min_price': sum(1 for v in data if v.get('starting_price_min')),
            'avg_price': sum(1 for v in data if v.get('starting_price_avg')),
            'deals': sum(1 for v in data if v.get('deals')),
            'awards': sum(1 for v in data if v.get('awards')),
            'website': sum(1 for v in data if v.get('website_url')),
        }
        for k, cnt in stats.items():
            print(f"  {k}: {cnt}/{len(data)}")