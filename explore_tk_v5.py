"""
TheKnot: reviews takes input: ReviewsInput! { filters: ReviewsFiltersInput! }
Now figure out ReviewsFiltersInput fields
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
        
        ids = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            const raw = s?.vendor?.vendorRaw || s?.vendor?.vendor || {};
            return { vendorId: raw.vendorId || '', uuid: raw.id || '', displayId: raw.displayId || '' };
        }''')
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 2000)};
                    return {ok: false, error: (d.errors?.[0]?.message || "no data").slice(0, 250)};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        print("Vendor ID: %s, UUID: %s" % (ids['vendorId'], ids['uuid']))
        
        # Try every possible ReviewsFiltersInput field
        print("\n=== ReviewsFiltersInput field discovery ===")
        filter_fields = ['vendorId', 'revieweeId', 'storefrontId', 'accountId', 'locationId',
                        'id', 'uuid', 'displayId', 'vendorUuid', 'storefrontUuid']
        
        for filter_field in filter_fields:
            for val_key in ['vendorId', 'uuid', 'displayId']:
                val = ids[val_key]
                if not val: continue
                q = 'reviews(input: { filters: { %s: "%s" } }) { items { id } }' % (filter_field, val)
                r = await try_q(q)
                if r.get('ok'):
                    print("  OK filters.{%s: %s}: WORKED! %s" % (filter_field, val[:8], r['data'][:200]))
                    break
                elif 'Unknown field' not in str(r.get('error', '')):
                    msg = r.get('error', '')[:120]
                    if 'required' not in msg.lower() and 'expected' not in msg.lower():
                        print("  ? filters.{%s}: %s" % (filter_field, msg))
        
        # Try all possible PaginatedReview.item fields
        print("\n=== PaginatedReview.items ===")
        for item_field in ['id', 'comment { text }', 'comment { id text createdAt }',
                          'rating', 'ratings { id }', 'ratings { id value }',
                          'reviewer { id name }', 'reviewerId', 'revieweeId',
                          'createdAt', 'title', 'summary', 'status']:
            # Use empty query that'll fail but tell us valid items fields
            q = 'reviews(input: { filters: { vendorId: "%s" } }) { items { %s } }' % (ids['vendorId'], item_field)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK items.%s: %s" % (item_field, r['data'][:200]))
            elif 'Cannot query' not in str(r.get('error', '')):
                if 'not found' not in str(r.get('error', '')).lower() and 'inconsistent' not in str(r.get('error', '')):
                    print("  ? items.%s: %s" % (item_field, r.get('error', '')[:100]))
        
        await browser.close()

asyncio.run(main())