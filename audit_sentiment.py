"""
Audit sentiment tagging accuracy — sample tagged reviews and manually inspect
1. Check negative-tagged reviews actually contain complaints
2. Check positive-tagged 5-star reviews look positive
3. Look for obvious mis-tags (e.g., vendor replies tagged as customer reviews)
"""
import psycopg2, random

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

print('=' * 70)
print('SENTIMENT TAGGING ACCURACY AUDIT')
print('=' * 70)

# Overall counts
cur.execute("SELECT sentiment, COUNT(*) FROM vendor_reviews GROUP BY sentiment")
total = {}
for r in cur.fetchall():
    total[r[0]] = r[1]
print(f"\nDistribution: {total}")

# ── TEST 1: Do negative-tagged reviews contain actual complaints? ──
print('\n' + '-' * 70)
print('TEST 1: Sample of NEGATIVE-tagged reviews (do they read as complaints?)')
print('-' * 70)
cur.execute("""
    SELECT review_text, rating, reviewer_name FROM vendor_reviews
    WHERE sentiment='negative' AND LENGTH(review_text) > 80
    ORDER BY RANDOM() LIMIT 8
""")
for r in cur.fetchall():
    print(f"\n[{r[1]}★] {r[2]}:")
    print(f"   {r[0][:220]}")

# ── TEST 2: Suspicious positives — do they contain complaint keywords? ──
print('\n' + '-' * 70)
print('TEST 2: POSITIVE-tagged reviews containing negative keywords (possible mis-tags)')
print('-' * 70)
cur.execute("""
    SELECT review_text, rating FROM vendor_reviews
    WHERE sentiment='positive'
      AND (review_text ILIKE '%disappointed%' OR review_text ILIKE '%terrible%'
           OR review_text ILIKE '%rude%' OR review_text ILIKE '%refund%'
           OR review_text ILIKE '%never showed%')
    LIMIT 5
""")
rows = cur.fetchall()
count = len(rows)
print(f"Found {count} suspicious positives:")
for r in rows:
    print(f"\n[{r[1]}★] {r[0][:250]}")

# ── TEST 3: Vendor replies stored as reviews (data quality issue) ──
print('\n' + '-' * 70)
print('TEST 3: Likely VENDOR REPLIES mis-stored as customer reviews')
print('-' * 70)
cur.execute("""
    SELECT COUNT(*) FROM vendor_reviews
    WHERE review_text ILIKE 'Hi %' AND (review_text ILIKE '%thank you for your review%'
        OR review_text ILIKE '%thank you so much%' OR review_text ILIKE '%thanks for the review%')
""")
vendor_replies = cur.fetchone()[0]
print(f"Reviews starting with vendor-style thank-you replies: {vendor_replies}")

cur.execute("""
    SELECT review_text FROM vendor_reviews
    WHERE review_text ILIKE 'Hi %' AND review_text ILIKE '%thank you for your review%'
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"   Example: {r[0][:150]}")

# ── TEST 4: Rating vs sentiment consistency ──
print('\n' + '-' * 70)
print('TEST 4: Rating vs sentiment consistency')
print('-' * 70)
cur.execute("""
    SELECT sentiment, ROUND(AVG(rating)::numeric, 2) as avg_rating,
           SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as high_rated,
           SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as low_rated,
           COUNT(*) as total
    FROM vendor_reviews WHERE rating IS NOT NULL
    GROUP BY sentiment
""")
for r in cur.fetchall():
    print(f"  {r[0]:10s}: avg {r[1]}★ | {r[2]}/{r[4]} rated 4+ | {r[3]}/{r[4]} rated ≤2")

# 5-star reviews tagged negative?
cur.execute("""
    SELECT COUNT(*) FROM vendor_reviews WHERE sentiment='negative' AND rating >= 5
""")
print(f"\n  5-star reviews tagged NEGATIVE: {cur.fetchone()[0]}")

cur.execute("""
    SELECT COUNT(*) FROM vendor_reviews WHERE sentiment='positive' AND rating <= 2
""")
print(f"  ≤2-star reviews tagged POSITIVE: {cur.fetchone()[0]}")

# Empty/short reviews
cur.execute("""
    SELECT COUNT(*) FROM vendor_reviews WHERE LENGTH(TRIM(review_text)) < 20
""")
print(f"\n  Reviews with <20 chars of text: {cur.fetchone()[0]}")

cur.close(); conn.close()
