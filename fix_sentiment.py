"""
Clean up sentiment tagging issues found in audit:
1. 1,026 vendor replies stored as customer reviews → re-tag by content
2. Title+body concatenation ("Jess is the Best!We are so lucky...") — text quality issue, not fixable easily
3. 11 untagged reviews
4. ≤2-star tagged positive (37) — keyword classifier missed these
5. 5,547 short (<20 char) reviews — mostly noise

Fix: re-run classification with rating as the dominant signal + flag vendor replies.
"""
import psycopg2, json

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Ensure column first
cur.execute("ALTER TABLE vendor_reviews ADD COLUMN IF NOT EXISTS is_vendor_reply BOOLEAN DEFAULT FALSE")
conn.commit()

VENDOR_REPLY_PATTERNS = [
    'thank you for your review', 'thanks for the review', 'thank you for the review',
    'we appreciate your feedback', 'thank you for sharing your experience',
    'we are truly sorry', "we're sorry to hear", 'we regret to hear',
    'thank you for taking the time to share', 'thanks for the feedback',
    'hi {},' ,  # placeholder
]

def is_vendor_reply(text):
    t = (text or '').lower()
    if any(p in t[:200] for p in VENDOR_REPLY_PATTERNS):
        return True
    # Starts with "Hi <Name>," or "Hey <Name>" followed by thanks/sorry
    if t.startswith(('hi ', 'hey ', 'hello ')):
        first_150 = t[:150]
        if any(w in first_150 for w in ['thank', 'sorry', 'appreciate', 'regret']):
            return True
    return False

# ── Fix 1: Flag vendor replies ──
cur.execute("""
    SELECT id, review_text FROM vendor_reviews
""")
rows = cur.fetchall()

vendor_reply_ids = []
for rid, text in rows:
    if is_vendor_reply(text):
        vendor_reply_ids.append(rid)

print(f"Vendor replies detected: {len(vendor_reply_ids)}")

if vendor_reply_ids:
    cur.execute("""
        UPDATE vendor_reviews 
        SET is_vendor_reply = TRUE,
            analysis_model = analysis_model || '+vendor-reply-flag'
        WHERE id = ANY(%s)
    """, (vendor_reply_ids,))
    print(f"Flagged {cur.rowcount} vendor replies")

# ── Add is_vendor_reply column if not exists ──
try:
    cur.execute("ALTER TABLE vendor_reviews ADD COLUMN IF NOT EXISTS is_vendor_reply BOOLEAN DEFAULT FALSE")
    conn.commit()
except Exception:
    conn.rollback()

# Re-flag now that column exists
if vendor_reply_ids:
    cur.execute("""
        UPDATE vendor_reviews 
        SET is_vendor_reply = TRUE
        WHERE id = ANY(%s)
    """, (vendor_reply_ids,))
    print(f"Flagged {cur.rowcount} vendor replies (column ensured)")

# ── Fix 2: Rating-dominant re-classification for mis-tagged ──
# Rule: rating >= 4 → positive; rating <= 2.5 → negative; else keep keyword result
cur.execute("""
    UPDATE vendor_reviews
    SET sentiment = CASE 
            WHEN rating >= 4 THEN 'positive'
            WHEN rating <= 2.5 THEN 'negative'
            ELSE 'neutral'
        END,
        sentiment_confidence = 0.9,
        analysis_model = 'rating-dominant-v2'
    WHERE (rating <= 2 AND sentiment = 'positive')
       OR (rating >= 4.5 AND sentiment = 'negative')
""")
print(f"Re-classified {cur.rowcount} rating-contradicted tags")

# ── Fix 3: Tag the 11 empty-sentiment rows ──
cur.execute("""
    UPDATE vendor_reviews
    SET sentiment = CASE 
            WHEN rating >= 4 THEN 'positive'
            WHEN rating <= 2.5 THEN 'negative'
            ELSE 'neutral'
        END,
        analysis_model = COALESCE(analysis_model, '') || '+rating-fill'
    WHERE sentiment = '' OR sentiment IS NULL
""")
print(f"Tagged {cur.rowcount} previously-empty sentiment rows")

conn.commit()

# ── Final distribution ──
cur.execute("SELECT sentiment, COUNT(*) FROM vendor_reviews GROUP BY sentiment")
print("\nFinal distribution:")
total_vr = 0
for r in cur.fetchall():
    total_vr += r[1]
    print(f"  {r[0] or '(empty)':10s}: {r[1]}")

cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE is_vendor_reply = TRUE")
print(f"\nVendor replies flagged (excluded from customer sentiment): {cur.fetchone()[0]}")
print(f"Total reviews: {total_vr}")

cur.close(); conn.close()