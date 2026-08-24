"""
Add review tables to wedding_vendors database
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

conn = psycopg2.connect(**DB)
conn.autocommit = True
cur = conn.cursor()

# reviews table — one row per individual review
reviews_sql = """
CREATE TABLE IF NOT EXISTS vendor_reviews (
    id SERIAL PRIMARY KEY,
    vendor_id INT REFERENCES vendors(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    
    -- Review content
    review_text TEXT NOT NULL,
    review_title TEXT DEFAULT '',
    rating NUMERIC(3,1),
    review_date DATE,
    reviewer_name TEXT DEFAULT '',
    reviewer_location TEXT DEFAULT '',
    
    -- Source references
    source_review_id TEXT,
    source_vendor_id TEXT,
    
    -- Sentiment analysis (filled by tagging pipeline)
    sentiment TEXT DEFAULT '' CHECK (sentiment IN ('', 'positive', 'neutral', 'negative')),
    sentiment_confidence NUMERIC(5,4) DEFAULT 0,
    
    -- Complaint categories (JSON array of tags)
    complaint_categories JSONB DEFAULT '[]'::jsonb,
    -- Praise categories (JSON array of tags)
    praise_categories JSONB DEFAULT '[]'::jsonb,
    -- Specific complaint/praise points (JSON array of {category, quote})
    complaint_points JSONB DEFAULT '[]'::jsonb,
    praise_points JSONB DEFAULT '[]'::jsonb,
    
    -- AI analysis
    ai_analysis JSONB DEFAULT '{}'::jsonb,
    analyzed_at TIMESTAMP,
    analysis_model TEXT DEFAULT '',
    
    -- Metadata
    scraped_at TIMESTAMP DEFAULT NOW(),
    first_seen TIMESTAMP DEFAULT NOW(),
    raw JSONB,
    
    -- Dedup: one review per source per source_review_id
    UNIQUE(source, source_review_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_vendor ON vendor_reviews(vendor_id);
CREATE INDEX IF NOT EXISTS idx_reviews_source ON vendor_reviews(source);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON vendor_reviews(sentiment);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON vendor_reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON vendor_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_complaints ON vendor_reviews(complaint_categories);
CREATE INDEX IF NOT EXISTS idx_reviews_praise ON vendor_reviews(praise_categories);
"""

for stmt in reviews_sql.split(';'):
    s = stmt.strip()
    if s:
        try:
            cur.execute(s)
            print(f"Executed: {s[:60]}...")
        except Exception as e:
            print(f"  Error: {e}")

conn.commit()

# Verify
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables: {tables}")

cur.execute("SELECT COUNT(*) FROM vendor_reviews")
print(f"Review count: {cur.fetchone()[0]}")

cur.execute("""
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'vendor_reviews' 
ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print(f"\nvendor_reviews columns: {cols}")

cur.close()
conn.close()
print("\n✅ Review schema ready")