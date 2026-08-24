"""
TheKnot reviews — the API works from /marketplace. The issue was the
nationwide_reviews.py was hitting a rate limit or session timeout.
This version: navigates to each vendor page (like scrape_tk_reviews.py did)
and paginates through ALL reviews.
"""
import asyncio, json, os, sys, time
from pathlib import Path

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')
sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}


def save_reviews_batch(reviews):
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
            """, (r['vid'], r['source'], r['text'][:5000], r['rating'], r['date'], r['reviewer'][:200], r['srid']))
            saved += cur.rowcount
        except:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return saved


def get_vendors():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, source_vendor_id, source_url, review_count
        FROM vendors 
        WHERE source = 'theknot' AND source_url != '' AND source_url IS NOT NULL AND review_count > 0
        ORDER BY review_count DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{'id': r[0], 'name': r[1], 'sid': r[2], 'url': r[3], 'rc': r[4]} for r in rows]


def get_existing_count(vendor_id):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE vendor_id=%s AND source='theknot'", (vendor_id,))
    c = cur.fetchone()[0]
    cur.close(); conn.close()
    return c


async def main():
    from playwright.async_api import async_playwright
    
    vendors = get_vendors()
    print(f"Vendors to process: {len(vendors)}")
    
    total_new = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        for i, v in enumerate(vendors):
            existing = get_existing_count(v['id'])
            needed = v['rc'] - existing
            
            print(f"\n[{i+1}/{len(vendors)}] {v['name'][:40]:40s} | TK:{v['rc']:5d} | Have:{existing:5d} | Need:{needed:5d}")
            
            if needed <= 0:
                print(f"  Already complete, skipping")
                continue
            
            try:
                # Navigate to vendor page to establish context
                page = await ctx.new_page()
                await page.goto(v['url'], wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                # Verify storefront ID matches
                actual_sid = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""')
                
                batch = []
                vendor_saved = 0
                num_pages = min(v['rc'] // 50 + 1, 60)  # Cap at ~3000 per vendor
                
                for pn in range(1, num_pages + 1):
                    query = ('reviews(input: { filters: { storefrontId: "%s" }, '
                            'orderBy: { type: date, sort: desc }, '
                            'pagination: { page: %d, size: 50 } }) { '
                            'totalCount pageInfo { hasNextPage } '
                            'nodes { id createdAt comment { content } '
                            'ratings { value name } '
                            'reviewer { firstName lastName email } } }') % (actual_sid, pn)
                    
                    result = await page.evaluate('''async function(qs) {
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
                        break
                    
                    reviews_data = data.get('reviews', {})
                    nodes = reviews_data.get('nodes', [])
                    if not nodes:
                        break
                    
                    for node in nodes:
                        text = (node.get('comment') or {}).get('content', '')
                        ratings_list = node.get('ratings', []) or []
                        values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                        avg = round(sum(values) / len(values), 1) if values else None
                        
                        rev = node.get('reviewer') or {}
                        rev_name = f"{rev.get('firstName', '')} {rev.get('lastName', '')}".strip()
                        
                        date_str = (node.get('createdAt', '') or '')[:10]
                        
                        batch.append({
                            'vid': v['id'],
                            'source': 'theknot',
                            'text': text[:5000] if text else '',
                            'rating': avg,
                            'date': date_str,
                            'reviewer': rev_name,
                            'srid': node.get('id', ''),
                        })
                    
                    has_next = reviews_data.get('pageInfo', {}).get('hasNextPage', False)
                    if not has_next:
                        break
                    
                    await asyncio.sleep(0.3)
                
                # Save this vendor's reviews
                if batch:
                    n = save_reviews_batch(batch)
                    vendor_saved = n
                    total_new += n
                
                print(f"  → Saved: {vendor_saved}")
                
                # Close page between vendors
                await page.close()
                
                # Rate limit between vendors  
                await asyncio.sleep(1.5)
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:80]}")
                try:
                    await page.close()
                except:
                    pass
        
        await browser.close()
    
    # Final stats
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE source='theknot'")
    tk_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vendor_reviews")
    grand_total = cur.fetchone()[0]
    cur.close(); conn.close()
    
    print(f"\n{'='*60}")
    print(f"NATIONWIDE THEKNOT REVIEW EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"New reviews saved: {total_new}")
    print(f"TheKnot total: {tk_total}")
    print(f"All sources total: {grand_total}")

if __name__ == '__main__':
    asyncio.run(main())