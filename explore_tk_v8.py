"""
TheKnot: vendorId is correct filter. Fix orderBy and pagination formats.
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
        
        # Try orderBy as object + pagination as object
        print("\n=== Object-style orderBy + pagination ===")
        for order_obj in ['{ createdAt: desc }', '{ createdAt: DESC }', '{ field: createdAt, direction: desc }', '{ field: createdAt, direction: DESC }']:
                for page_obj in ['{ pageSize: 5, page: 1 }', '{ size: 5, number: 1 }', '{ first: 5, offset: 0 }', '{ limit: 5, offset: 0 }', '{ take: 5, skip: 0 }']:
                    q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: %s, pagination: %s }) { items { id } totalCount }' % (vendor_id, order_obj, page_obj)
                    r = await try_q(q)
                    if r.get('ok'):
                        print("  OK orderBy=%s pagination=%s: %s" % (order_obj[:40], page_obj[:30], r['data'][:200]))
                        break
                    elif 'orderBy' in str(r.get('error', '')):
                        pass
                    elif 'pagination' in str(r.get('error', '')):
                        pass
                    else:
                        err = r.get('error', '')[:100]
                        if not any(x in err for x in ['Unknown', 'Expected', 'Syntax', 'did you mean']):
                            print("  ? %s %s: %s" % (order_obj[:40], page_obj[:30], err))
        
        # Also try: orderBy as a regular string but with quotes
        print("\n=== String orderBy with quotes ===")
        q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: "createdAt_desc", pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % vendor_id
        r = await try_q(q)
        print("  String: %s" % json.dumps(r, default=str)[:200])
        
        q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: createdAt_desc, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % vendor_id
        r = await try_q(q)
        print("  Enum: %s" % json.dumps(r, default=str)[:200])
        
        # Try the correct format — orderBy { field: direction }
        for order_val in ['createdAt_desc', 'createdAt_asc', 'createdAt_DESC', 'rating_desc', 'rating_asc']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: %s, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, order_val)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK orderBy=%s: %s" % (order_val, r['data'][:200]))
                break
            else:
                err = r.get('error', '')[:80]
                if 'Expected value' not in err:
                    print("  ? %s: %s" % (order_val, err))
        
        # Maybe orderBy is a literal string passed as "ORDER_BY"
        for order_str in ['createdAt_desc', 'CREATED_AT_DESC', 'createdAt_DESC']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { direction: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, order_str)
            r = await try_q(q)
            if r.get('ok'):
                print("  OK {direction: %s}: %s" % (order_str, r['data'][:200]))
                break
        
        await browser.close()

asyncio.run(main())