"""
Check Zola scraper output quality
"""
import json
from pathlib import Path

out_dir = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# Find latest Zola output
files = sorted(out_dir.glob('zola_*.json'))
if not files:
    print("No Zola output files found")
    exit()

latest = files[-1]
print(f"File: {latest.name}")
print(f"Size: {latest.stat().st_size:,} bytes\n")

with open(latest) as f:
    vendors = json.load(f)

print(f"Total vendors: {len(vendors)}")
print(f"Successful: {sum(1 for v in vendors if v.get('scrape_success'))}")
print()

# Show sample fields
print("=== SAMPLE VENDOR ===")
if vendors:
    v = vendors[0]
    for k, val in sorted(v.items()):
        if val and val != [] and val != {} and val != 0 and val != '':
            s = json.dumps(val, default=str)
            if len(s) > 250:
                s = s[:250] + '...'
            print(f"  {k}: {s}")

# Stats
print(f"\n=== STATS ===")
fields_filled = {k: sum(1 for v in vendors if v.get(k) and v[k] not in [[], {}, '', 0, 0.0])
                 for k in ['name', 'phone', 'website_url', 'email', 'city', 'state', 
                           'price_tier', 'starting_price', 'review_count', 'star_rating', 'description']}
for k, cnt in sorted(fields_filled.items()):
    pct = cnt * 100 / len(vendors)
    print(f"  {k}: {cnt}/{len(vendors)} ({pct:.0f}%)")
    if k == 'star_rating' and cnt > 0:
        ratings = [v.get('star_rating', 0) for v in vendors]
        print(f"    Range: {min(ratings):.1f} - {max(ratings):.1f}")

# Vendors with phone
phones = [(v['name'], v['phone']) for v in vendors if v.get('phone')]
print(f"\nVendors with phone ({len(phones)}):")
for name, phone in phones[:5]:
    print(f"  {name}: {phone}")

# Vendors with email
emails = [(v['name'], v['email']) for v in vendors if v.get('email')]
print(f"\nVendors with email ({len(emails)}):")
for name, email in emails[:5]:
    print(f"  {name}: {email}")

# Price info
prices = [(v['name'], v.get('price_tier', ''), v.get('starting_price', '')) for v in vendors if v.get('starting_price') or v.get('price_tier')]
print(f"\nVendors with pricing ({len(prices)}):")
for name, tier, price in prices[:8]:
    print(f"  {name}: tier={tier} price={price}")