"""
Set up wedding vendors database and schema
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    'host': 'localhost',
    'port': 54329,
    'user': 'postgres',
    'password': 'devpass',
}

# Step 1: Create database
conn = psycopg2.connect(**DB_CONFIG)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Check if DB exists
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'wedding_vendors'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE wedding_vendors")
    print("Created database: wedding_vendors")
else:
    print("Database wedding_vendors already exists")

cur.close()
conn.close()

# Step 2: Create schema
conn = psycopg2.connect(**DB_CONFIG, dbname='wedding_vendors')
cur = conn.cursor()

schema_sql = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT '',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    vendors_found INT DEFAULT 0,
    vendors_successful INT DEFAULT 0,
    status TEXT DEFAULT 'running',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    
    source TEXT NOT NULL,
    source_vendor_id TEXT NOT NULL,
    source_url TEXT,
    
    name TEXT NOT NULL,
    category TEXT,
    city TEXT,
    state TEXT,
    
    phone TEXT,
    email TEXT,
    website_url TEXT,
    
    starting_price_min NUMERIC(10,2),
    starting_price_avg NUMERIC(10,2),
    starting_price_range TEXT,
    price_tier TEXT,
    
    star_rating NUMERIC(3,1),
    review_count INT,
    
    description TEXT,
    headline TEXT,
    ad_tier TEXT,
    vendor_tier TEXT,
    service_area TEXT,
    year_founded INT,
    team_size INT,
    travel_distance INT,
    
    facebook_url TEXT,
    instagram_username TEXT,
    pinterest_username TEXT,
    
    awards JSONB DEFAULT '[]'::jsonb,
    deals JSONB DEFAULT '[]'::jsonb,
    
    theknot_display_id TEXT,
    ww_biz_id TEXT,
    zola_slug TEXT,
    
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    scrape_run_id INT REFERENCES scrape_runs(id),
    raw_data JSONB,
    
    UNIQUE(source, source_vendor_id)
);

CREATE INDEX IF NOT EXISTS idx_vendors_source ON vendors(source);
CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name);
CREATE INDEX IF NOT EXISTS idx_vendors_city ON vendors(city, state);
CREATE INDEX IF NOT EXISTS idx_vendors_category ON vendors(category);
CREATE INDEX IF NOT EXISTS idx_vendors_last_seen ON vendors(last_seen);
"""

# Execute each statement separately
for statement in schema_sql.split(';'):
    stmt = statement.strip()
    if stmt:
        try:
            cur.execute(stmt)
            print(f"Executed: {stmt[:60]}...")
        except Exception as e:
            print(f"  Error: {e}")

conn.commit()

# Verify
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables created: {tables}")

cur.execute("SELECT count(*) FROM vendors")
print(f"Current vendor count: {cur.fetchone()[0]}")

cur.close()
conn.close()
print("\n✅ Database setup complete")