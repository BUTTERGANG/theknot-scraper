"""
Final comprehensive stats after nationwide build
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=54329, user='postgres', password='devpass', dbname='wedding_vendors')
cur = conn.cursor()

print("=" * 60)
print("FINAL NATIONWIDE DATASET STATS")
print("=" * 60)

# Vendors
cur.execute('SELECT COUNT(*) FROM vendors')
total_vendors = cur.fetchone()[0]
cur.execute("SELECT source, COUNT(*) FROM vendors GROUP BY source ORDER BY COUNT(*) DESC")
by_source = cur.fetchall()

print(f"\nVENDORS: {total_vendors}")
for s, c in by_source:
    print(f"  {s}: {c}")

# Reviews
cur.execute('SELECT COUNT(*) FROM vendor_reviews')
total_reviews = cur.fetchone()[0]
cur.execute("SELECT source, COUNT(*) FROM vendor_reviews GROUP BY source ORDER BY COUNT(*) DESC")
rev_by_source = cur.fetchall()
cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE LENGTH(review_text) > 50")
with_text = cur.fetchone()[0]
cur.execute('SELECT COUNT(DISTINCT vendor_id) FROM vendor_reviews')
vendors_with = cur.fetchone()[0]

print(f"\nREVIEWS: {total_reviews}")
for s, c in rev_by_source:
    print(f"  {s}: {c}")
print(f"  With substantial text: {with_text}")
print(f"  Vendors with reviews: {vendors_with}")

# Rating distribution
cur.execute("""
    SELECT 
        SUM(CASE WHEN rating >= 4.5 THEN 1 ELSE 0 END) as high,
        SUM(CASE WHEN rating >= 3.5 AND rating < 4.5 THEN 1 ELSE 0 END) as mid,
        SUM(CASE WHEN rating >= 1 AND rating < 3.5 THEN 1 ELSE 0 END) as low
    FROM vendor_reviews WHERE rating IS NOT NULL
""")
r = cur.fetchone()
print(f"\nRATING DISTRIBUTION:")
print(f"  4.5-5★: {r[0]}")
print(f"  3.5-4.5★: {r[1]}")
print(f"  Below 3.5★: {r[2]}")

# Categories covered
cur.execute("""
    SELECT v.category, COUNT(DISTINCT v.id) as vendors, COUNT(vr.id) as reviews
    FROM vendors v LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id
    WHERE v.category != '' AND v.category IS NOT NULL
    GROUP BY v.category ORDER BY COUNT(vr.id) DESC
""")
print(f"\nBY CATEGORY:")
for r in cur.fetchall():
    print(f"  {r[0]:25s} | {r[1]:4d} vendors | {r[2]:5d} reviews")

# Geographic coverage
cur.execute("""
    SELECT v.state, COUNT(DISTINCT v.id) as vendors, COUNT(vr.id) as reviews
    FROM vendors v LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id
    WHERE v.state != '' AND v.state IS NOT NULL
    GROUP BY v.state ORDER BY COUNT(vr.id) DESC LIMIT 15
""")
print(f"\nTOP STATES:")
for r in cur.fetchall():
    print(f"  {r[0]:5s} | {r[1]:4d} vendors | {r[2]:5d} reviews")

cur.close()
conn.close()