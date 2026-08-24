"""
TheKnot: Full working query. Lowercase enums, page/size, find PaginatedReview field.
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
                    if (d.data) {
                        return {ok: true, data: JSON.stringify(d.data).slice(0, 3000)};
                    }
                    const msgs = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "no data";
                    return {ok: false, error: msgs};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        base = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 5 } })' % vendor_id
        
        print("\n=== PaginatedReview field names ===")
        for field in [
            'nodes { id }', 'results { id }', 'data { id }', 'entries { id }',
            'list { id }', 'edges { node { id } }', 'items { id }',
            'totalCount', 'count', 'total', 'pageInfo { hasNextPage }',
            'reviews { id }',
        ]:
            q = base + ' { ' + field + ' }'
            r = await try_q(q)
            if r.get('ok'):
                print("  OK %s: %s" % (field[:30], r['data'][:300]))
            elif 'Cannot query' not in r.get('error', ''):
                print("  ? %s: %s" % (field[:30], r.get('error', '')[:100]))
        
        # Try nodes with review fields
        print("\n=== Full review fields via nodes ===")
        for field in [
            'nodes { id comment { text createdAt } rating ratings { id value } }',
            'nodes { id comment { text } rating createdAt title reviewer { name } }',
            'nodes { id comment { text } rating ratings { id value } reviewer { id name } }',
        ]:
            q = base + ' { ' + field + ' }'
            r = await try_q(q)
            if r.get('ok'):
                print("  OK: %s" % r['data'][:500])
            elif 'Cannot query' not in r.get('error', ''):
                print("  ? %s" % r.get('error', '')[:120])
        
        await browser.close()

asyncio.run(main())