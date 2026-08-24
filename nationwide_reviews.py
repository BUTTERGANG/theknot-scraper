"""
Fix nationwide review extraction — use correct field names from __INITIAL_STATE__
The search results have: reviewSummary: {count, overallRating}, NOT reviewsCount/stars
"""
import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')
sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}


def save_review_batch(reviews):
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
            """, (r['vendor_db_id'], r['source'], r['text'][:5000],
                  r['rating'], r['date'], r['reviewer'][:200], r['source_review_id']))
            saved += 1
        except:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return saved


def get_vendors_with_reviews():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, source_vendor_id, review_count, city, state 
        FROM vendors 
        WHERE source = 'theknot' AND review_count > 0
        ORDER BY review_count DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{'db_id': r[0], 'name': r[1], 'storefront_id': r[2], 
             'review_count': r[3], 'city': r[4], 'state': r[5]} for r in rows]


async def main():
    from playwright.async_api import async_playwright
    
    # Get all vendors with reviews from DB
    vendors = get_vendors_with_reviews()
    print(f"Vendors with reviews in DB: {len(vendors)}")
    
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
        
        batch_reviews = []
        
        for i, v in enumerate(vendors):
            sid = v['storefront_id']
            name = v['name']
            
            if i % 20 == 0 or i < 5:
                print(f"\n[{i+1}/{len(vendors)}] {name[:40]:40s} | {v['city']}, {v['state']} | {v['review_count']} reviews")
            
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
                
                vendor_saved = 0
                for node in nodes:
                    text = (node.get('comment') or {}).get('content', '')
                    ratings_list = node.get('ratings', []) or []
                    values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                    avg = round(sum(values) / len(values), 1) if values else None
                    
                    rev = node.get('reviewer') or {}
                    rev_name = f"{rev.get('firstName', '')} {rev.get('lastName', '')}".strip()
                    
                    date_str = (node.get('createdAt', '') or '')[:10]
                    
                    batch_reviews.append({
                        'vendor_db_id': v['db_id'],
                        'source': 'theknot',
                        'text': text[:5000] if text else '',
                        'rating': avg,
                        'date': date_str,
                        'reviewer': rev_name,
                        'source_review_id': node.get('id', ''),
                    })
                    vendor_saved += 1
                
                # Continue pagination for high-review vendors
                total_count = reviews_data.get('totalCount', 0)
                
                if total_count > 50:
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
                                'vendor_db_id': v['db_id'],
                                'source': 'theknot',
                                'text': text[:5000] if text else '',
                                'rating': avg,
                                'date': date_str,
                                'reviewer': rev_name,
                                'source_review_id': node.get('id', ''),
                            })
                            vendor_saved += 1
                        
                        await asyncio.sleep(0.2)
                
                if i < 5 or i % 20 == 19:
                    print(f"  → {vendor_saved} reviews extracted")
                
                # Save batch periodically
                if len(batch_reviews) >= 500:
                    n = save_review_batch(batch_reviews)
                    total_saved += n
                    batch_reviews = []
                    print(f"  [batch saved: {n}]")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                pass
        
        # Final save
        if batch_reviews:
            n = save_review_batch(batch_reviews)
            total_saved += n
        
        await session_page.close()
        await browser.close()
    
    # Final stats
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE source = 'theknot'")
    tk_reviews = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vendor_reviews")
    all_reviews = cur.fetchone()[0]
    cur.close(); conn.close()
    
    print(f"\n{'='*60}")
    print(f"NATIONWIDE REVIEW EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Reviews saved this run: {total_saved}")
    print(f"TheKnot reviews total: {tk_reviews}")
    print(f"All sources total: {all_reviews}")

if __name__ == '__main__':
    asyncio.run(main())