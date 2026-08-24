"""
Debug why nationwide upsert returned 0 new vendors
"""
import json, psycopg2
from pathlib import Path

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

# Check what discovery found
out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/nationwide')
files = sorted(out.glob('discovery_*.json'))
if not files:
    print("No discovery file")
    exit()

with open(files[-1]) as f:
    vendors = json.load(f)

print(f"Discovery file: {files[-1].name}")
print(f"Vendors: {len(vendors)}")

# Show first vendor
v = vendors[0]
print(f"\nSample vendor:")
for k, val in sorted(v.items()):
    if val:
        s = str(val)
        if len(s) > 100:
            s = s[:100] + '...'
        print(f"  {k}: {s}")

# Check DB for existing storefront_id
conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Count by source_vendor_id prefix (storefront UUIDs are stored there)
cur.execute("""
    SELECT source_vendor_id FROM vendors 
    WHERE source = 'theknot' AND source_vendor_id IS NOT NULL AND source_vendor_id != ''
""")
existing_ids = set(r[0] for r in cur.fetchall())
print(f"\nExisting TheKnot IDs in DB: {len(existing_ids)}")
for sid in list(existing_ids)[:5]:
    print(f"  {sid}")

# Check how many discovery vendors have matching storefront_id in existing DB
matches = 0
no_match = 0
for v in vendors[:50]:
    if v.get('storefront_id') in existing_ids:
        matches += 1
    else:
        no_match += 1

print(f"\nOf first 50 vendors:")
print(f"  Matching existing: {matches}")
print(f"  New (should insert): {no_match}")

# Test upsert manually with one vendor
test_v = [v for v in vendors if v.get('storefront_id') not in existing_ids][:1]
if test_v:
    tv = test_v[0]
    print(f"\nTesting upsert for: {tv['name']} ({tv['storefront_id']})")
    
    cur.execute("""
        INSERT INTO vendors (
            source, source_vendor_id, source_url,
            name, category, city, state,
            starting_price_range,
            star_rating, review_count,
            service_area, ad_tier, vendor_tier, claimed_status,
            awards
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, source_vendor_id) DO UPDATE SET
            name = EXCLUDED.name,
            star_rating = EXCLUDED.star_rating,
            review_count = EXCLUDED.review_count,
            last_seen = NOW()
        RETURNING id, xmax = 0 AS is_insert
    """, (
        'theknot', tv['storefront_id'], tv.get('url', ''),
        tv['name'], tv.get('category', ''), tv.get('city', ''), tv.get('state', ''),
        tv.get('starting_price_range', ''),
        float(tv.get('rating', 0) or 0),
        int(tv.get('review_count', 0) or 0),
        tv.get('service_area', ''),
        tv.get('ad_tier', ''),
        tv.get('vendor_tier', ''),
        tv.get('claimed_status', ''),
        json.dumps(tv.get('awards', [])),
    ))
    result = cur.fetchone()
    conn.commit()
    print(f"  Result: id={result[0]}, was_insert={result[1]}")

cur.close()
conn.close()