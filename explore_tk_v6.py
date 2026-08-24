"""
TheKnot: reviews needs BOTH filters AND orderBy. Add orderBy and test filters.
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
        
        print("IDs: %s" % json.dumps({k: (v[:12] + '...') for k, v in ids.items() if v}))
        
        # First: what values does ReviewsOrderByInput accept?
        print("\n=== ReviewsOrderByInput values ===")
        for order_val in ['createdAt_ASC', 'createdAt_DESC', 'createdAt asc', 'createdAt desc',
                         'updatedAt_ASC', 'updatedAt_DESC', 'rating_ASC', 'rating_DESC',
                         'createdAt', '-createdAt', '{ createdAt: asc }', '{ createdAt: desc }']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: %s }) { items { id } }' % (ids['vendorId'], order_val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK orderBy=%s: %s" % (order_val, r['data'][:200]))
                break
            elif 'Unknown' not in str(r.get('error', '')) and 'Expected' not in str(r.get('error', '')):
                print("  ? orderBy=%s: %s" % (order_val, r.get('error', '')[:100]))
        
        # Try with orderBy as object
        print("\n=== orderBy as object ===")
        for order_obj in ['{ createdAt: asc }', '{ createdAt: desc }', '{ updatedAt: desc }',
                         '{ createdAt: ASC }', '{ createdAt: DESC }']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: %s }) { items { id } }' % (ids['vendorId'], order_obj)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK orderBy=%s: %s" % (order_obj, r['data'][:300]))
                break
            elif 'Unknown' not in str(r.get('error', '')):
                print("  ? orderBy=%s: %s" % (order_obj, r.get('error', '')[:100]))
        
        # Try with just page/limit (no orderBy — maybe it's optional in practice)
        print("\n=== Page/limit (no orderBy) ===")
        q = 'reviews(input: { filters: { vendorId: "%s" }, page: 1, limit: 10 }) { items { id } totalCount }' % ids['vendorId']
        r = await try_q(q)
        print("  page/limit: %s" % json.dumps(r, default=str)[:400])
        
        # Try with different filter field names + orderBy
        print("\n=== Filter fields with orderBy ===")
        for filter_field in ['vendorId', 'revieweeId', 'storefrontId', 'accountId', 'locationId',
                           'id', 'uuid', 'displayId']:
            val = ids.get(filter_field, '')
            if not val: continue
            for order_obj in ['createdAt_desc', '{ createdAt: desc }', 'createdAt_DESC']:
                q = 'reviews(input: { filters: { %s: "%s" }, orderBy: %s }) { items { id } }' % (filter_field, val, order_obj)
                r = await try_q(q)
                if r.get('ok'):
                    print("  OK %s with orderBy=%s: %s" % (filter_field, order_obj, r['data'][:200]))
                    break
                elif 'Unknown field' in str(r.get('error', '')):
                    pass # wrong field name
                elif 'orderBy' in str(r.get('error', '')):
                    pass # orderBy format issue
                else:
                    print("  ? %s: %s" % (filter_field, r.get('error', '')[:100]))
                if r.get('ok'): break
        
        await browser.close()

asyncio.run(main())