# TheKnot Wedding Vendor Intelligence Scraper

Nationwide wedding vendor data pipeline: scrapes vendor listings + full review text from TheKnot, Zola, and WeddingWire into PostgreSQL for competitive intelligence and market analysis.

## Dataset Summary

| Metric | Count |
|--------|-------|
| Vendors tracked | 1,734 |
| Reviews collected | 32,613 |
| Metros covered | 28 US cities |
| Categories | DJs (787), Planners (836), Photographers, Venues, Florists, Caterers |
| States | 22 |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
├──────────────┬──────────────┬───────────────────────────┤
│   TheKnot    │    Zola      │      WeddingWire           │
│  GraphQL API │ __NEXT_DATA__│  JSON-LD / DOM              │
└──────┬───────┴──────┬───────┴──────────┬────────────────┘
       │              │                   │
       ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                 PLAYWRIGHT SCRAPERS                      │
│  Visible browser via Xvfb (:99) — anti-detection        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              POSTGRESQL (localhost:54329)                │
│  vendors (1,734) │ vendor_reviews (32,613) │ scrape_runs│
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│            SENTIMENT TAGGER + DASHBOARD                  │
│  Rule-based v1: 96% positive, 3% negative               │
│  29 complaint/praise categories auto-detected            │
└─────────────────────────────────────────────────────────┘
```

## Key Files

### Production Scrapers

| File | Source | Method | Status |
|------|--------|--------|--------|
| `theknot_scraper_v2.py` | TheKnot | `__INITIAL_STATE__` Redux extraction | ✅ Working |
| `zola_scraper.py` | Zola | `__NEXT_DATA__` Next.js SSR extraction | ✅ Working |
| `weddingwire_scraper.py` | WeddingWire | JSON-LD `application/ld+json` parsing | ✅ Working |
| `scrape_tk_reviews.py` | TheKnot | GraphQL API (cracked) | ✅ Working |
| `scrape_zola_reviews.py` | Zola | Scroll-triggered DOM extraction | ✅ Working |
| `sentiment_tagger_bulk.py` | DB | Rule-based keyword + rating classification | ✅ Working |
| `nationwide_tk_v3.py` | TheKnot | Nationwide multi-metro pipeline | ✅ Working |
| `db_writer.py` | All | Unified upsert to PostgreSQL | ✅ Working |

### Database Schema

```sql
-- vendors: 1,734 rows
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,           -- 'theknot', 'zola', 'weddingwire'
    source_vendor_id TEXT NOT NULL, -- unique ID per source
    name TEXT NOT NULL,
    category TEXT,                  -- 'wedding-djs', 'wedding-planners', etc.
    city TEXT, state TEXT,
    phone TEXT, email TEXT, website_url TEXT,
    starting_price_min NUMERIC(10,2),
    star_rating NUMERIC(3,1),
    review_count INT,
    description TEXT,
    ad_tier TEXT, vendor_tier TEXT,
    facebook_url TEXT, instagram_username TEXT,
    awards JSONB DEFAULT '[]',
    deals JSONB DEFAULT '[]',
    UNIQUE(source, source_vendor_id)
);

-- vendor_reviews: 32,613 rows
CREATE TABLE vendor_reviews (
    id SERIAL PRIMARY KEY,
    vendor_id INT REFERENCES vendors(id),
    source TEXT NOT NULL,
    review_text TEXT NOT NULL,
    rating NUMERIC(3,1),
    review_date DATE,
    reviewer_name TEXT,
    sentiment TEXT DEFAULT '',       -- 'positive', 'neutral', 'negative'
    sentiment_confidence NUMERIC(5,4),
    complaint_categories JSONB,      -- ["communication", "billing", ...]
    praise_categories JSONB,         -- ["quality", "professionalism", ...]
    analyzed_at TIMESTAMP,
    UNIQUE(source, source_review_id)
);

-- scrape_runs: audit trail
CREATE TABLE scrape_runs (
    id SERIAL PRIMARY KEY,
    source TEXT, category TEXT, city TEXT, state TEXT,
    started_at TIMESTAMP, completed_at TIMESTAMP,
    vendors_found INT, vendors_successful INT,
    status TEXT
);
```

### TheKnot GraphQL API (Cracked)

```
Endpoint: https://svc.theknotww.com/reviews-api/graphql
Method: POST
Headers:
  Content-Type: application/json
  x-tenant-id: tk-us

Query structure:
  reviews(input: {
    filters: { storefrontId: "<vendor-uuid>" },
    orderBy: { type: date, sort: desc },
    pagination: { page: N, size: 50 }
  }) {
    totalCount
    pageInfo { hasNextPage }
    nodes {
      id createdAt title
      comment { content }          -- review text
      ratings { value name }       -- Quality/Value/Response Time/Flexibility/Professionalism
      reviewer { firstName lastName email }
    }
  }

Storefront UUID found in: window.__INITIAL_STATE__.vendor.vendorRaw.id
```

### Zola Review Extraction

Zola embeds reviews in the DOM after scroll. Navigate to `/wedding-vendors/{category}/{slug}`, scroll through page, extract from `[class*="reviews-section"]` elements.

Fields available: reviewer name, rating (1-5), date, full review text.

### Anti-Detection Requirements

| Site | Protection | Solution |
|------|-----------|----------|
| TheKnot | DataDome | Visible browser (Xvfb), residential IP, session cookies |
| Zola | Cloudflare (moderate) | Playwright stealth args, random delays |
| WeddingWire | Cloudflare (moderate) | Standard Playwright setup |

**Setup:**
```bash
apt install xvfb
pip install playwright && playwright install chromium
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99 PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright
```

## Running the Pipeline

```bash
# 1. Set up database
python setup_db.py && python setup_review_db.py

# 2. Discover vendors across metros
python nationwide_build.py          # 28 metros × 3 categories

# 3. Pull reviews
python nationwide_tk_v3.py         # TheKnot reviews via GraphQL
python scale_zola_reviews.py       # Zola reviews via DOM

# 4. Tag sentiment
python sentiment_tagger_bulk.py    # ~4,000 reviews/sec

# 5. Export dashboard data + build dashboard
python export_dashboard.py
python embed_data.py               # Creates index.html (standalone)
```

## Dashboard

Open `index.html` in any browser — fully standalone with embedded data and Chart.js visualizations.

Features:
- Sentiment overview (doughnut chart)
- Rating distribution
- Category breakdown table
- Geographic analysis (top states)
- Complaint/praise analysis
- Top performers
- Auto-generated insights

## Known Limitations

- **Review coverage**: 121/1,734 vendors have reviews stored. Many newly discovered vendors haven't been processed yet.
- **Sentiment model**: Rule-based keyword matching (v1). Misses nuanced mixed-sentiment reviews ("great but pricey"). LLM-based tagging would improve accuracy.
- **WeddingWire reviews**: Found 92 DOM elements but requires complex JS interaction; not yet implemented.
- **Google Maps/Yelp**: Require paid APIs ($0.75-14.99/1K calls) due to aggressive anti-bot protection.
- **TheKnot pagination**: Capped at 20 pages (1,000 reviews) per vendor per run to avoid rate limiting.
- **DataDome**: Adapts over time. A single IP doing sustained scraping will eventually get flagged.

## License

MIT — educational/research purposes only. Respect TheKnot/Zola/WeddingWire Terms of Service.