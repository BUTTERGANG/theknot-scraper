"""
TheKnot: ReviewsOrderByInput { sort: Sort! }. Find Sort enum values.
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
        
        # Try Sort enum values
        print("\n=== Sort enum values ===")
        sort_values = [
            'CREATED_AT_DESC', 'CREATED_AT_ASC', 'createdAt_DESC', 'createdAt_ASC',
            'UPDATED_AT_DESC', 'UPDATED_AT_ASC', 'RATING_DESC', 'RATING_ASC',
            'CREATED_AT', 'UPDATED_AT', 'RATING',
            'DATE_DESC', 'DATE_ASC', 'NEWEST', 'OLDEST',
            'createdAt_desc', 'createdAt_asc', 'updatedAt_desc', 'updatedAt_asc',
            'rating_desc', 'rating_asc',
        ]
        
        for sort_val in sort_values:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { sort: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, sort_val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK sort=%s: %s" % (sort_val, r['data'][:200]))
                break
            else:
                err = r.get('error', '')[:80]
                if 'Unknown' in err or 'Expected' in err or 'Syntax' in err:
                    pass  # Expected enum format errors
                elif 'sort' in err.lower():
                    # Sort field not provided means we have wrong format
                    pass
                else:
                    print("  ? %s: %s" % (sort_val, err))
        
        # Try PageSizePaginationInput format
        print("\n=== PageSizePaginationInput ===")
        pag_formats = [
            '{ pageSize: 5, page: 1 }', '{ size: 5, number: 1 }',
            '{ limit: 5, page: 1 }', '{ first: 5, after: null }',
            '{ take: 5, skip: 0 }', '{ offset: 0, limit: 5 }',
        ]
        for pag in pag_formats:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { sort: CREATED_AT_DESC }, pagination: %s }) { items { id } totalCount }' % (vendor_id, pag)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK pag=%s: %s" % (pag[:30], r['data'][:200]))
                break
            else:
                err = r.get('error', '')[:60]
                if 'Unknown' in err or 'Expected' in err:
                    pass
                else:
                    print("  ? %s: %s" % (pag[:30], err))
        
        await browser.close()

asyncio.run(main())