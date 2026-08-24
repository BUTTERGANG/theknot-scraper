"""
Nationwide review extraction v3 — ALL TheKnot vendors (not just review_count>0)
Processes every vendor, pulls all available reviews via GraphQL.
Skips vendors already fully scraped.
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime

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


def update_review_count(vendor_id, count):
    """Update vendor's review_count after we discover actual total"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("UPDATE vendors SET review_count = %s WHERE id = %s", (count, vendor_id))
    conn.commit()
    cur.close()
    conn.close()


def get_all_theknot_vendors():
    """Get ALL TheKnot vendors — not just ones with review_count > 0"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, source_vendor_id, source_url, review_count, city, state
        FROM vendors 
        WHERE source = 'theknot' 
        AND source_vendor_id != '' AND source_vendor_id IS NOT NULL
        ORDER BY id
    """)
    rows = cur.fetchall()
    # Get existing review counts per vendor
    cur.execute("""
        SELECT vendor_id, COUNT(*) FROM vendor_reviews 
        WHERE source = 'theknot' GROUP BY vendor_id
    """)
    existing_map = dict(cur.fetchall())
    cur.close(); conn.close()
    
    result = []
    for r in rows:
        vid = r[0]
        existing = existing_map.get(vid, 0)
        result.append({
            'id': vid,
            'name': r[1],
            'sid': r[2],
            'url': r[3] or '',
            'db_rc': r[4] or 0,
            'city': r[5] or '',
            'state': r[6] or '',
            'existing': existing,
        })
    return result


async def main():
    from playwright.async_api import async_playwright
    
    vendors = get_all_theknot_vendors()
    print(f"Total TheKnot vendors: {len(vendors)}")
    print(f"Already have some reviews: {sum(1 for v in vendors if v['existing'] > 0)}")
    print(f"Zero reviews so far: {sum(1 for v in vendors if v['existing'] == 0)}")
    
    # Sort by existing reviews ascending (process unprocessed ones first)
    # But put high-review-count vendors first since they're most valuable
    # Vendors we haven't checked yet (existing=0) go first
    
    total_new = 0
    processed = 0
    skipped_complete = 0
    no_reviews_on_tk = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        session_page = await ctx.new_page()
        
        # Establish session via marketplace page
        print("\nEstablishing session...")
        await session_page.goto('https://www.theknot.com/marketplace',
                               wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        async def graphql_fetch(query_str):
            """Fetch from GraphQL API"""
            return await session_page.evaluate('''async function(qs) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + qs + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return JSON.stringify(d.data);
                    const msgs = d.errors ? d.errors.map(function(e){return e.message;}).join("; ") : "";
                    return JSON.stringify({error: msgs});
                } catch(e) { return JSON.stringify({error: e.message}); }
            }''', query_str)
        
        batch = []
        start_time = time.time()
        
        for i, v in enumerate(vendors):
            sid = v['sid']
            
            # Progress update every 25 vendors or at start
            if i < 5 or i % 25 == 24:
                elapsed = time.time() - start_time
                rate = (i + 1) / max(elapsed, 1) * 60
                eta_min = (len(vendors) - i) / max(rate / 60, 0.01) / 60
                pct = (i + 1) * 100 // len(vendors)
                print(f"\n[{i+1}/{len(vendors)}] ({pct}%) | {total_new} saved | ~{eta_min:.0f}min remaining")
            
            # Quick probe: just get totalCount
            probe_q = ('reviews(input: { filters: { storefrontId: "%s" }, '
                      'orderBy: { type: date, sort: desc }, '
                      'pagination: { page: 1, size: 50 } }) { totalCount }') % sid
            
            try:
                result = await graphql_fetch(probe_q)
                data = json.loads(result)
                
                if 'error' in data:
                    continue
                
                tk_total = data.get('reviews', {}).get('totalCount', 0)
                
                if tk_total == 0:
                    no_reviews_on_tk += 1
                    continue
                
                # Update DB with actual count
                if tk_total != v['db_rc']:
                    update_review_count(v['id'], tk_total)
                
                # Check if we already have enough
                if v['existing'] >= tk_total:
                    skipped_complete += 1
                    continue
                
                # Pull reviews — paginate
                num_pages = min(tk_total // 50 + 1, 20)  # Cap at 1000/vendor
                vendor_new = 0
                
                for pn in range(1, num_pages + 1):
                    full_q = ('reviews(input: { filters: { storefrontId: "%s" }, '
                             'orderBy: { type: date, sort: desc }, '
                             'pagination: { page: %d, size: 50 } }) { '
                             'totalCount pageInfo { hasNextPage } '
                             'nodes { id createdAt comment { content } '
                             'ratings { value name } '
                             'reviewer { firstName lastName email } } }') % (sid, pn)
                    
                    r_full = await graphql_fetch(full_q)
                    d_full = json.loads(r_full)
                    
                    if 'error' in d_full:
                        break
                    
                    rd = d_full.get('reviews', {})
                    nodes = rd.get('nodes', [])
                    if not nodes:
                        break
                    
                    for node in nodes:
                        text = (node.get('comment') or {}).get('content', '')
                        
                        ratings_list = node.get('ratings') or []
                        values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                        avg = round(sum(values) / len(values), 1) if values else None
                        
                        rev = node.get('reviewer') or {}
                        rev_name = f"{rev.get('firstName', '')} {rev.get('lastName', '')}".strip()
                        date_str = (node.get('createdAt', '') or '')[:10]
                        
                        if text and len(text) > 10:
                            batch.append({
                                'vid': v['id'],
                                'source': 'theknot',
                                'text': text[:5000],
                                'rating': avg,
                                'date': date_str,
                                'reviewer': rev_name,
                                'srid': node.get('id', ''),
                            })
                    
                    has_next = rd.get('pageInfo', {}).get('hasNextPage', False)
                    if not has_next:
                        break
                    
                    await asyncio.sleep(0.2)  # Rate limit between pages
                
                # Save batch periodically
                if len(batch) >= 300:
                    n = save_reviews_batch(batch)
                    total_new += n
                    vendor_new += n
                    batch = []
                
                processed += 1
                
                if i < 10 or i % 25 == 24:
                    print(f"  {v['name'][:35]:35s} | TK:{tk_total:5d} | Had:{v['existing']:5d}")
                
                await asyncio.sleep(0.5)  # Rate limit between vendors
                
            except Exception as e:
                pass
        
        # Final save
        if batch:
            n = save_reviews_batch(batch)
            total_new += n
        
        await session_page.close()
        await browser.close()
    
    elapsed = time.time() - start_time
    
    # Final stats
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE source='theknot'")
    tk_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vendor_reviews")
    grand_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT vendor_id) FROM vendor_reviews WHERE source='theknot'")
    tk_vendors_with = cur.fetchone()[0]
    cur.close(); conn.close()
    
    print(f"\n{'='*60}")
    print(f"NATIONWIDE THEKNOT REVIEW EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Vendors processed: {processed}")
    print(f"No reviews on TK: {no_reviews_on_tk}")
    print(f"Already complete (skipped): {skipped_complete}")
    print(f"New reviews saved: {total_new}")
    print(f"TheKnot total: {tk_total}")
    print(f"TheKnot vendors with reviews: {tk_vendors_with}")
    print(f"All sources total: {grand_total}")

if __name__ == '__main__':
    asyncio.run(main())