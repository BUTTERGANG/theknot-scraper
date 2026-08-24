"""
TheKnot: reviews needs filters + orderBy + pagination. Full query test.
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
            return {
                vendorId: raw.vendorId || '',
                uuid: raw.id || '',
                displayId: raw.displayId || '',
                accountId: raw.accountId || '',
                locationId: raw.locationId || '',
            };
        }''')
        print("IDs loaded")
        
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
        
        # Try full query with all 3 required inputs
        print("\n=== Full query: filters + orderBy + pagination ===")
        for filter_field in ['vendorId', 'id', 'uuid', 'accountId', 'locationId', 'displayId', 'storefrontId']:
            val = ids.get(filter_field, '')
            if not val: continue
            
            q = 'reviews(input: { filters: { %s: "%s" }, orderBy: createdAt_DESC, pagination: { pageSize: 10, page: 1 } }) { items { id comment { text } rating } totalCount }' % (filter_field, val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK %s: %s" % (filter_field, r['data'][:300]))
                # If it works, try more item fields
                if '"items"' in r['data']:
                    # Full query with all item fields
                    q2 = 'reviews(input: { filters: { %s: "%s" }, orderBy: createdAt_DESC, pagination: { pageSize: 5, page: 1 } }) { items { id comment { text createdAt } rating ratings { id value } reviewer { id name } createdAt title } totalCount }' % (filter_field, val)
                    r2 = await try_q(q2)
                    print("    Full fields: %s" % r2.get('data', r2.get('error', ''))[:500])
                    break
            elif 'Unknown field' not in str(r.get('error', '')):
                print("  ? %s: %s" % (filter_field, r.get('error', '')[:120]))
        
        # Try with PageSizePaginationInput different format
        print("\n=== Different pagination formats ===")
        q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: createdAt_DESC, pagination: { size: 10, number: 1 } }) { items { id } totalCount }' % ids['vendorId']
        r = await try_q(q)
        print("  size/number: %s" % json.dumps(r, default=str)[:200])
        
        q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: createdAt_DESC, pagination: { first: 10, offset: 0 } }) { items { id } totalCount }' % ids['vendorId']
        r = await try_q(q)
        print("  first/offset: %s" % json.dumps(r, default=str)[:200])
        
        await browser.close()

asyncio.run(main())