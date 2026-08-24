"""
TheKnot: ReviewsOrderByInput { type: ReviewsOrderByType! }. Find enum values.
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
        
        # Find ReviewsOrderByType enum values
        print("\n=== ReviewsOrderByType enum values ===")
        type_values = [
            # Standard enum naming
            'CREATED_AT_ASC', 'CREATED_AT_DESC', 'UPDATED_AT_ASC', 'UPDATED_AT_DESC',
            'RATING_ASC', 'RATING_DESC', 'NEWEST_FIRST', 'OLDEST_FIRST',
            'HIGHEST_RATED', 'LOWEST_RATED', 'MOST_RECENT', 'LEAST_RECENT',
            'DATE_ASC', 'DATE_DESC', 'RELEVANCE', 'POPULARITY',
            # CamelCase
            'createdAt_ASC', 'createdAt_DESC', 'updatedAt_ASC', 'updatedAt_DESC',
            'rating_ASC', 'rating_DESC',
            # Simple values
            'NEWEST', 'OLDEST', 'BEST', 'WORST', 'RECENT',
        ]
        
        for type_val in type_values:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, type_val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK type=%s: %s" % (type_val, r['data'][:300]))
                break
            else:
                err = r.get('error', '')[:80]
                # Only show if it's NOT the standard "Expected type" error
                if not any(x in err for x in ['Expected value', 'Unknown enum', 'Syntax Error']):
                    print("  ? %s: %s" % (type_val, err))
        
        # Try PageSizePaginationInput field exploration
        print("\n=== PageSizePaginationInput fields ===")
        pag_formats = [
            '{ pageSize: 5, page: 1 }', '{ size: 5, number: 1 }',
            '{ first: 5, after: null }', '{ take: 5, skip: 0 }',
            '{ limit: 5, offset: 0 }', '{ itemsPerPage: 5, pageNumber: 1 }',
            '{ pageSize: 5 }', '{ limit: 5 }', '{ first: 5 }',
            '{ page: 1, pageSize: 10 }',
        ]
        for pag in pag_formats:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: CREATED_AT_DESC }, pagination: %s }) { items { id } totalCount }' % (vendor_id, pag)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK pag=%s: %s" % (pag[:35], r['data'][:200]))
                break
            else:
                err = r.get('error', '')[:60]
                if 'Field' in err and 'required' in err:
                    # Pagination format partially recognized
                    print("  %s: %s" % (pag[:35], err))
        
        # Try the simplest query possible
        print("\n=== Simple no-filters query ===")
        q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: CREATED_AT_DESC }, pagination: { pageSize: 5, page: 1 } }) { items { id comment { text } rating } }' % vendor_id
        r = await try_q(q)
        print("  Result: %s" % json.dumps(r, default=str)[:500])
        
        await browser.close()

asyncio.run(main())