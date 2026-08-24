"""
Bulk upsert all 1,563 nationwide vendors + pull reviews via GraphQL
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/nationwide')


def bulk_upsert(vendors):
    """Upsert all vendors in a single transaction for speed"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    inserted = 0
    updated = 0
    
    for v in vendors:
        try:
            cur.execute("""
                INSERT INTO vendors (
                    source, source_vendor_id, source_url,
                    name, category, city, state,
                    starting_price_range,
                    star_rating, review_count,
                    service_area, ad_tier, vendor_tier, claimed_status,
                    awards
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source, source_vendor_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    city = COALESCE(EXCLUDED.city, vendors.city),
                    state = COALESCE(EXCLUDED.state, vendors.state),
                    starting_price_range = COALESCE(EXCLUDED.starting_price_range, vendors.starting_price_range),
                    star_rating = EXCLUDED.star_rating,
                    review_count = EXCLUDED.review_count,
                    service_area = COALESCE(EXCLUDED.service_area, vendors.service_area),
                    ad_tier = COALESCE(EXCLUDED.ad_tier, vendors.ad_tier),
                    vendor_tier = COALESCE(EXCLUDED.vendor_tier, vendors.vendor_tier),
                    claimed_status = COALESCE(EXCLUDED.claimed_status, vendors.claimed_status),
                    awards = EXCLUDED.awards,
                    last_seen = NOW()
                RETURNING id, (xmax = 0) AS was_insert
            """, (
                v.get('source', 'theknot'),
                v.get('storefront_id', ''),
                v.get('url', ''),
                v.get('name', ''),
                v.get('category', ''),
                v.get('city', ''),
                v.get('state', ''),
                v.get('starting_price_range', ''),
                float(v.get('rating', 0) or 0),
                int(v.get('review_count', 0) or 0),
                v.get('service_area', ''),
                v.get('ad_tier', ''),
                v.get('vendor_tier', ''),
                v.get('claimed_status', ''),
                json.dumps(v.get('awards', [])),
            ))
            row = cur.fetchone()
            if row[1]:  # was_insert
                inserted += 1
            else:
                updated += 1
            
            # Store db_id back on the vendor dict
            v['db_id'] = row[0]
            
        except Exception as e:
            print(f"  Upsert error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return inserted, updated


def save_review_batch(reviews):
    """Save multiple reviews in one transaction"""
    if not reviews:
        return 0
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    saved = 0
    for r in reviews:
        try:
            cur.execute("""
                INSERT INTO vendor_reviews (vendor_id, source, review_text, rating, review_date, reviewer_name, source_review_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, source_review_id) DO NOTHING
            """, (
                r['vendor_db_id'], r['source'], r['text'][:5000],
                r['rating'], r['date'], r['reviewer'][:200], r['source_review_id']
            ))
            saved += 1
        except:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return saved


async def main():
    from playwright.async_api import async_playwright
    
    # Load discovery results
    out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/nationwide')
    files = sorted(out.glob('discovery_*.json'))
    
    if not files:
        print("No discovery file found")
        return
    
    with open(files[-1]) as f:
        vendors = json.load(f)
    
    print(f"Loaded {len(vendors)} discovered vendors")
    
    # Phase 1: Bulk upsert
    print("\n=== PHASE 1: BULK UPSERT ===")
    inserted, updated = bulk_upsert(vendors)
    print(f"  Inserted: {inserted}")
    print(f"  Updated: {updated}")
    
    # Sort by review count descending
    vendors.sort(key=lambda x: x.get('review_count', 0), reverse=True)
    
    # Filter to vendors with reviews
    with_reviews = [v for v in vendors if v.get('review_count', 0) > 0]
    print(f"  Vendors with reviews: {len(with_reviews)}")
    
    # Phase 2: Pull reviews via GraphQL
    print(f"\n=== PHASE 2: REVIEW EXTRACTION ({len(with_reviews)} vendors) ===")
    
    total_saved = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        session_page = await ctx.new_page()
        
        # Establish session
        await session_page.goto('https://www.theknot.com/marketplace',
                               wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        print("  Session established")
        
        batch_reviews = []
        
        for i, v in enumerate(with_reviews):
            sid = v.get('storefront_id', '')
            name = v.get('name', '')
            
            if i % 50 == 0:
                pct = i * 100 // max(1, len(with_reviews))
                print(f"\n[{i}/{len(with_reviews)}] ({pct}%) | Total saved so far: {total_saved}")
                # Commit batch periodically
                if batch_reviews:
                    n = save_review_batch(batch_reviews)
                    total_saved += n
                    batch_reviews = []
            
            if not sid:
                continue
            
            try:
                query = ('reviews(input: { filters: { storefrontId: "%s" }, '
                        'orderBy: { type: date, sort: desc }, '
                        'pagination: { page: 1, size: 50 } }) { '
                        'totalCount pageInfo { hasNextPage } '
                        'nodes { id createdAt comment { content } '
                        'ratings { value name } '
                        'reviewer { firstName lastName email } } }') % sid
                
                result = await session_page.evaluate('''async function(qs) {
                    try {
                        const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                            method: "POST",
                            headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                            body: JSON.stringify({query: "query { " + qs + " }"})
                        });
                        const d = await r.json();
                        if (d.data) return JSON.stringify(d.data);
                        return JSON.stringify({error: d.errors ? d.errors.map(function(e){return e.message;}).join("; ") : ""});
                    } catch(e) { return JSON.stringify({error: e.message}); }
                }''', query)
                
                data = json.loads(result)
                
                if 'error' in data:
                    continue
                
                reviews_data = data.get('reviews', {})
                nodes = reviews_data.get('nodes', [])
                
                for node in nodes:
                    text = (node.get('comment') or {}).get('content', '')
                    ratings_list = node.get('ratings', []) or []
                    values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                    avg = round(sum(values) / len(values), 1) if values else None
                    
                    rev = node.get('reviewer') or {}
                    rev_name = f"{rev.get('firstName', '')} {rev.get('lastName', '')}".strip()
                    
                    date_str = (node.get('createdAt', '') or '')[:10]
                    
                    batch_reviews.append({
                        'vendor_db_id': v.get('db_id'),
                        'source': 'theknot',
                        'text': text[:5000],
                        'rating': avg,
                        'date': date_str,
                        'reviewer': rev_name,
                        'source_review_id': node.get('id', ''),
                    })
                
                # Continue pagination for high-review vendors
                total_count = reviews_data.get('totalCount', 0)
                has_next = reviews_data.get('pageInfo', {}).get('hasNextPage', False)
                
                if total_count > 50 and has_next:
                    num_pages = min(total_count // 50 + 1, 10)  # Cap at 500 per vendor
                    
                    for pn in range(2, num_pages + 1):
                        query_p = ('reviews(input: { filters: { storefrontId: "%s" }, '
                                  'orderBy: { type: date, sort: desc }, '
                                  'pagination: { page: %d, size: 50 } }) { '
                                  'pageInfo { hasNextPage } '
                                  'nodes { id createdAt comment { content } '
                                  'ratings { value name } '
                                  'reviewer { firstName lastName email } } }') % (sid, pn)
                        
                        result_p = await session_page.evaluate('''async function(qs) {
                            try {
                                const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                                    method: "POST",
                                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                                    body: JSON.stringify({query: "query { " + qs + " }"})
                                });
                                const d = await r.json();
                                if (d.data) return JSON.stringify(d.data);
                                return JSON.stringify({});
                            } catch(e) { return JSON.stringify({}); }
                        }''', query_p)
                        
                        data_p = json.loads(result_p).get('reviews', {})
                        nodes_p = data_p.get('nodes', [])
                        
                        for node in nodes_p:
                            text = (node.get('comment') or {}).get('content', '')
                            ratings_list = node.get('ratings', []) or []
                            values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                            avg = round(sum(values) / len(values), 1) if values else None
                            
                            rev = node.get('reviewer') or {}
                            rev_name = f"{rev.get('firstName', '')} {rev.get('lastName', '')}".strip()
                            date_str = (node.get('createdAt', '') or '')[:10]
                            
                            batch_reviews.append({
                                'vendor_db_id': v.get('db_id'),
                                'source': 'theknot',
                                'text': text[:5000],
                                'rating': avg,
                                'date': date_str,
                                'reviewer': rev_name,
                                'source_review_id': node.get('id', ''),
                            })
                        
                        await asyncio.sleep(0.2)
                
                # Rate limit between vendors
                await asyncio.sleep(0.5)
                
            except Exception as e:
                pass
        
        # Save remaining batch
        if batch_reviews:
            n = save_review_batch(batch_reviews)
            total_saved += n
        
        await session_page.close()
        await browser.close()
    
    # Final stats
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM vendors WHERE source = %s', ('theknot',))
    tk_vendors = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM vendor_reviews WHERE source = %s', ('theknot',))
    tk_reviews = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM vendor_reviews')
    all_reviews = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE LENGTH(review_text) > 50")
    with_text = cur.fetchone()[0]
    cur.close(); conn.close()
    
    print(f"\n{'='*60}")
    print(f"NATIONWIDE BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"TheKnot vendors in DB: {tk_vendors}")
    print(f"TheKnot reviews in DB: {tk_reviews}")
    print(f"Reviews saved this run: {total_saved}")
    print(f"Total reviews across all sources: {all_reviews}")
    print(f"With substantial text (>50 chars): {with_text}")

if __name__ == '__main__':
    asyncio.run(main())