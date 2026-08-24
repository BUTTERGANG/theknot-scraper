"""
Verify database contents
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=54329, user='postgres', password='devpass', dbname='wedding_vendors')
cur = conn.cursor()

print('=== DATABASE SUMMARY ===')

cur.execute('SELECT COUNT(*) FROM vendors')
print(f'Total vendors: {cur.fetchone()[0]}')

cur.execute('SELECT source, COUNT(*) FROM vendors GROUP BY source ORDER BY source')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

cur.execute('SELECT COALESCE(category, \'?\'), COUNT(*) FROM vendors GROUP BY category ORDER BY COUNT(*) DESC')
print(f'\nBy category:')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

cur.execute("""
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN phone != '' AND phone IS NOT NULL THEN 1 ELSE 0 END) as with_phone,
  SUM(CASE WHEN email != '' AND email IS NOT NULL THEN 1 ELSE 0 END) as with_email,
  SUM(CASE WHEN website_url != '' AND website_url IS NOT NULL THEN 1 ELSE 0 END) as with_website,
  SUM(CASE WHEN starting_price_min IS NOT NULL OR starting_price_avg IS NOT NULL THEN 1 ELSE 0 END) as with_pricing,
  SUM(CASE WHEN star_rating > 0 THEN 1 ELSE 0 END) as with_rating,
  SUM(CASE WHEN review_count > 0 THEN 1 ELSE 0 END) as with_reviews,
  SUM(CASE WHEN city != '' AND city IS NOT NULL THEN 1 ELSE 0 END) as with_city
FROM vendors
""")
r = cur.fetchone()
print(f'\nCoverage:')
print(f'  Phone:   {r[1]}/{r[0]} ({r[1]*100//r[0]}%)')
print(f'  Email:   {r[2]}/{r[0]} ({r[2]*100//r[0]}%)')
print(f'  Website: {r[3]}/{r[0]} ({r[3]*100//r[0]}%)')
print(f'  Pricing: {r[4]}/{r[0]} ({r[4]*100//r[0]}%)')
print(f'  Rating:  {r[5]}/{r[0]} ({r[5]*100//r[0]}%)')
print(f'  Reviews: {r[6]}/{r[0]} ({r[6]*100//r[0]}%)')
print(f'  City:    {r[7]}/{r[0]} ({r[7]*100//r[0]}%)')

print(f'\n=== SAMPLE THEKNOT VENDORS (with contact) ===')
cur.execute("""
SELECT name, city, state, phone, email, starting_price_min, star_rating, review_count 
FROM vendors WHERE source='theknot' AND phone != '' LIMIT 5
""")
for r in cur:
    price = f'${r[5]:.0f}' if r[5] else '?'
    print(f'  {r[0][:35]:35s} | {r[3] or "—":15s} | {r[4] or "—":30s} | {price:>6s} | {r[6]}★({r[7]})')

print(f'\n=== PRICING SNAPSHOT ===')
cur.execute("""
SELECT source, ROUND(AVG(starting_price_min)) as avg_min,
       ROUND(AVG(starting_price_avg)) as avg_avg,
       MIN(starting_price_min) as lo,
       MAX(starting_price_avg) as hi
FROM vendors WHERE starting_price_min IS NOT NULL GROUP BY source
""")
for r in cur:
    print(f'  {r[0]}: avg min=${r[1]} avg midpoint=${r[2]} range=${r[3]}-${r[4]}')

print(f'\n=== RECENT SCRAPE RUNS ===')
cur.execute("""
SELECT source, category, city, state, vendors_found, vendors_successful, started_at
FROM scrape_runs ORDER BY started_at DESC LIMIT 10
""")
for r in cur:
    cat = (r[1] or '?')[:25]
    print(f'  {r[0][:10]:>12s} | {cat:25s} | {r[2] or "?":15s} | {str(r[3] or ""):2s} | {r[4]}/{r[5]}')

cur.close()
conn.close()

print(f'\n✅ DB verification complete')