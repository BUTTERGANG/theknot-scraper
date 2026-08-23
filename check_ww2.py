"""
Check WeddingWire output quality
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

ww = sorted(out.glob('ww_*.json'))[-1]
with open(ww) as f:
    data = json.load(f)

print(f"WeddingWire: {len(data)} vendors")
print(f"File: {ww.name}")

if data:
    v = data[0]
    print(f"\nSample vendor:")
    for k, val in sorted(v.items()):
        if val:
            s = json.dumps(val, default=str)[:200]
            print(f"  {k}: {s}")

# Stats
stats = {
    'name': sum(1 for v in data if v.get('name')),
    'rating': sum(1 for v in data if v.get('rating')),
    'review_count': sum(1 for v in data if v.get('review_count')),
    'price': sum(1 for v in data if v.get('starting_price')),
    'url': sum(1 for v in data if v.get('biz_url')),
    'description': sum(1 for v in data if v.get('description')),
}
print(f"\nStats:")
for k, cnt in stats.items():
    pct = cnt * 100 / len(data)
    print(f"  {k}: {cnt}/{len(data)} ({pct:.0f}%)")

# Show ratings range
ratings = [(v['name'], v['rating'], v['review_count'], v['starting_price']) 
           for v in data if v.get('rating')]
print(f"\nVendors with ratings ({len(ratings)}):")
for name, rate, cnt, price in ratings[:5]:
    print(f"  {name}: {rate}★ ({cnt} reviews) {price}")

# Show prices
prices = [(v['name'], v['starting_price']) for v in data if v.get('starting_price')]
print(f"\nVendors with prices ({len(prices)}):")
for name, price in prices[:5]:
    print(f"  {name}: {price}")