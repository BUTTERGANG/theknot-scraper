"""
Final DB stats after full scrape
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=54329, user='postgres', password='devpass', dbname='wedding_vendors')
cur = conn.cursor()

cur.execute('SELECT source, COUNT(*) FROM vendor_reviews GROUP BY source ORDER BY COUNT(*) DESC')
by_source = dict(cur.fetchall())

cur.execute('SELECT COUNT(*) FROM vendor_reviews')
total = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM vendor_reviews WHERE review_text IS NOT NULL AND LENGTH(review_text) > 50')
with_text = cur.fetchone()[0]

cur.execute('SELECT COUNT(DISTINCT vendor_id) FROM vendor_reviews')
vendors_with = cur.fetchone()[0]

cur.execute('SELECT ROUND(AVG(rating), 2) as avg_rating, MIN(rating), MAX(rating) FROM vendor_reviews WHERE rating IS NOT NULL')
r = cur.fetchone()

print("=" * 60)
print("FINAL REVIEW DATABASE STATS")
print("=" * 60)
print(f"Total reviews: {total}")
print(f"With text: {with_text}")
print(f"Vendors with reviews: {vendors_with}")
print(f"Avg rating: {r[0]} (range {r[1]}-{r[2]})")

for s, c in by_source.items():
    print(f"\n{s}: {c} reviews")
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE source=%s AND LENGTH(review_text) > 50", (s,))
    print(f"  With text: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(DISTINCT vendor_id) FROM vendor_reviews WHERE source=%s", (s,))
    print(f"  Vendors: {cur.fetchone()[0]}")

cur.close()
conn.close()