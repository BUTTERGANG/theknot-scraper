"""
TheKnot: totalCount works with storefrontId! Now get nodes with review data.
The pagination JS had quote issues. Fix and get actual reviews.
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def main():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        storefront_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""')
        print("Storefront ID: %s" % storefront_id)
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) {
                        return {ok: true, data: JSON.stringify(d.data).slice(0, 5000)};
                    }
                    const msgs2 = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "no data";
                    return {ok: false, error: msgs2};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        # Try getting actual review nodes
        print("\n=== Get nodes with review text ===")
        
        # Simple first
        q1 = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 3 } }) { totalCount nodes { id } }' % storefront_id
        r = await try_q(q1)
        print("  nodes.id: %s" % json.dumps(r, default=str)[:300])
        
        # Add comment
        q2 = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 3 } }) { totalCount nodes { id comment { id text } } }' % storefront_id
        r = await try_q(q2)
        print("  nodes.comment: %s" % json.dumps(r, default=str)[:500])
        
        # Full fields
        q3 = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 5 } }) { totalCount pageInfo { hasNextPage } nodes { id rating createdAt title comment { text } reviewer { name } } }' % storefront_id
        r = await try_q(q3)
        print("\n  Full query:")
        if r.get('ok'):
            print("    OK! %s" % r['data'][:2000])
        else:
            print("    Error: %s" % r.get('error', '')[:300])
        
        # If that works, paginate all reviews
        if r.get('ok'):
            print("\n=== Paginating ALL reviews ===")
            total_count = 0
            all_reviews = []
            
            for page_num in range(1, 60):  # Max 60 pages of 50 = 3000 reviews (enough)
                try:
                    q = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: %d, size: 50 } }) { totalCount pageInfo { hasNextPage } nodes { id rating createdAt title comment { text } reviewer { name } } }' % (storefront_id, page_num)
                    result = await try_q(q)
                    
                    if not result.get('ok'):
                        print("  Page %d error: %s" % (page_num, result.get('error', '')[:100]))
                        break
                    
                    data = json.loads(result['data'])['reviews']
                    nodes = data.get('nodes', [])
                    
                    if not nodes:
                        break
                    
                    all_reviews.extend(nodes)
                    
                    if page_num == 1:
                        total_count = data.get('totalCount', 0)
                        print("  Total reviews: %d" % total_count)
                    
                    has_next = data.get('pageInfo', {}).get('hasNextPage', False)
                    
                    if not has_next or len(all_reviews) >= total_count:
                        print("  Done at page %d. Fetched %d/%d reviews." % (page_num, len(all_reviews), total_count))
                        break
                        
                    # Small delay between pages
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"  Page {page_num} exception: {e}")
                    break
            
            # Save to file
            out_path = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/reviews/theknot_georgestreet.json')
            out_path.parent.mkdir(exist_ok=True, parents=True)
            with open(out_path, 'w') as f:
                json.dump(all_reviews, f, indent=2, default=str)
            print(f"\nSaved {len(all_reviews)} reviews to {out_path}")
            
            # Show samples
            if all_reviews:
                for rev in all_reviews[:3]:
                    text = (rev.get('comment', {}) or {}).get('text', '')
                    print(f"\n  [{rev.get('rating')}★] {(rev.get('reviewer') or {}).get('name', '?')}")
                    print(f"    {text[:200]}...")
        
        await browser.close()

asyncio.run(main())