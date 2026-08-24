"""
TheKnot: ReviewsOrderByInput has BOTH type AND sort. Try both together.
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
        
        vendor_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.vendorId || ""')
        print("Vendor ID: %s" % vendor_id)
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 3000)};
                    return {ok: false, error: (d.errors?.[0]?.message || "no data").slice(0, 300)};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        print("\n=== type + sort combinations ===")
        for type_val in ['CREATED_AT_DESC', 'CREATED_AT_ASC', 'RATING_DESC', 'RATING_ASC',
                        'NEWEST_FIRST', 'RECENT', 'MOST_RECENT', 'DATE_DESC', 'DATE_ASC',
                        'createdAt_DESC', 'CREATED_AT', 'DATE']:
            for sort_val in ['ASC', 'DESC', 'asc', 'desc', 'RELEVANCE', 'DEFAULT', 'NEWEST']:
                q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: %s, sort: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, type_val, sort_val)
                r = await try_q(q)
                if r.get('ok'):
                    print("  OK type=%s sort=%s: %s" % (type_val, sort_val, r['data'][:300]))
                    return
                else:
                    err = r.get('error', '')[:80]
                    if not any(x in err for x in ['Expected', 'Unknown', 'Syntax', 'required']):
                        print("  ? type=%s sort=%s: %s" % (type_val, sort_val, err))
        
        # Also try with only sort (no type)
        print("\n=== sort only (no type) ===")
        for sort_val in ['ASC', 'DESC', 'asc', 'desc', 'RELEVANCE', 'CREATED_AT']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { sort: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, sort_val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK sort=%s: %s" % (sort_val, r['data'][:300]))
                break
            
        await browser.close()

asyncio.run(main())