"""
Check what review data exists in our DB and explore TheKnot review structure
"""
import json, psycopg2, os

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Check raw_data of a TheKnot vendor
cur.execute("SELECT name, raw_data FROM vendors WHERE source = 'theknot' AND raw_data IS NOT NULL LIMIT 1")
row = cur.fetchone()
if row:
    name = row[0]
    raw = row[1]
    print(f"=== RAW DATA FROM DB: {name} ===\n")
    print(f"Top keys: {list(raw.keys())}")
    
    # Search for review-related keys
    for k in sorted(raw.keys()):
        v = raw[k]
        if 'review' in k.lower() or 'review' in str(v)[:50].lower():
            print(f"\n  {k}: {type(v).__name__}")
            s = json.dumps(v, default=str)
            print(f"    {s[:500]}")
    
    # Also check the vendor_raw inside it
    print(f"\n--- Checking for reviewSummary or review objects ---")
    # Look deeply
    def find_review_keys(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                rk = k.lower()
                if 'review' in rk or 'rating' in rk or 'comment' in rk or 'feedback' in rk:
                    s = json.dumps(v, default=str)
                    print(f"  {path}.{k} ({type(v).__name__}) = {s[:400]}")
                find_review_keys(v, f"{path}.{k}")
        elif isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
            find_review_keys(obj[0], f"{path}[0]")
    
    find_review_keys(raw)

# Also check volume of reviews we could get
print(f"\n=== EXISTING REVIEW METRICS IN DB ===\n")
cur.execute("""
SELECT source, 
       COUNT(*) as vendors,
       SUM(review_count) as total_reviews,
       ROUND(AVG(star_rating), 2) as avg_rating,
       ROUND(AVG(review_count)) as avg_reviews_per_vendor
FROM vendors 
WHERE review_count > 0 
GROUP BY source
ORDER BY source
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} vendors, {r[2]} total reviews, {r[3]}★ avg, ~{r[4]}/vendor")

print(f"\nTotal review count in existing data: ", end="")
cur.execute("SELECT SUM(review_count) FROM vendors WHERE review_count > 0")
print(cur.fetchone()[0])

cur.close()
conn.close()

print(f"\n✅ Done")