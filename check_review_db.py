"""
Final review DB status
"""
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM vendor_reviews')
total = cur.fetchone()[0]
print(f'Total reviews: {total}')

cur.execute('SELECT source, COUNT(*) FROM vendor_reviews GROUP BY source')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

cur.execute("""
SELECT v.name, v.source, COUNT(vr.id) 
FROM vendor_reviews vr JOIN vendors v ON v.id=vr.vendor_id 
GROUP BY v.name, v.source ORDER BY COUNT(vr.id) DESC LIMIT 10
""")
print(f'\nTop vendors by review count:')
for r in cur:
    print(f'  {r[0][:45]:45s} | {r[1]:8s} | {r[2]} reviews')

cur.execute("SELECT sentiment, COUNT(*) FROM vendor_reviews WHERE sentiment != '' GROUP BY sentiment ORDER BY COUNT(*) DESC")
print(f'\nSentiment distribution:')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE jsonb_array_length(complaint_categories) > 0 OR jsonb_array_length(praise_categories) > 0")
print(f'Tagged with categories: {cur.fetchone()[0]}')

cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE sentiment = 'negative'")
neg = cur.fetchone()[0]
print(f'Negative reviews: {neg}')

if neg > 0:
    cur.execute("""
        SELECT vr.review_text, v.name, vr.rating FROM vendor_reviews vr 
        JOIN vendors v ON v.id=vr.vendor_id 
        WHERE vr.sentiment = 'negative' LIMIT 3
    """)
    print(f'\nSample negative reviews:')
    for r in cur:
        print(f'  [{r[1]}] ({r[2]}★) {r[0][:200]}')

# Also show top complaint categories
cur.execute("""
    SELECT cat, COUNT(*) FROM (
        SELECT jsonb_array_elements_text(complaint_categories) as cat 
        FROM vendor_reviews WHERE jsonb_array_length(complaint_categories) > 0
    ) t GROUP BY cat ORDER BY COUNT(*) DESC LIMIT 10
""")
print(f'\nTop complaint categories:')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

# Show top praise categories
cur.execute("""
    SELECT cat, COUNT(*) FROM (
        SELECT jsonb_array_elements_text(praise_categories) as cat 
        FROM vendor_reviews WHERE jsonb_array_length(praise_categories) > 0
    ) t GROUP BY cat ORDER BY COUNT(*) DESC LIMIT 10
""")
print(f'\nTop praise categories:')
for r in cur:
    print(f'  {r[0]}: {r[1]}')

cur.close()
conn.close()