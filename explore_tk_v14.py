"""
TheKnot: storefrontId is the required filter! Full query test.
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
            return { uuid: raw.id || '', vendorId: raw.vendorId || '', displayId: raw.displayId || '' };
        }''')
        print("IDs: %s" % json.dumps(ids))
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) {
                        const msgs = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "";
                        return {ok: true, data: JSON.stringify(d.data).slice(0, 3000), partial_errors: msgs};
                    }
                    const msgs2 = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "no data";
                    return {ok: false, error: msgs2};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        # Test storefrontId as the filter
        print("\n=== storefrontId as filter ===")
        base = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 5 } })' % ids['uuid']
        
        for field in [
            'totalCount',
            'nodes { id comment { text createdAt } rating }',
            'nodes { id comment { text } rating ratings { id value } reviewer { name } createdAt title }',
            'nodes { id rating } totalCount pageInfo { hasNextPage }',
        ]:
            q = base + ' { ' + field + ' }'
            r = await try_q(q)
            print("  %s" % field[:50])
            if r.get('ok'):
                print("    OK! %s" % r['data'][:500])
                if r.get('partial_errors'):
                    print("    Partial errors: %s" % r['partial_errors'][:200])
                break
            else:
                print("    Error: %s" % r.get('error', '')[:200])
        
        # Try full pagination
        print("\n=== Full pagination (all reviews) ===")
        all_reviews = await page.evaluate('''async function(vid) {
            let all = [];
            let page_num = 1;
            let hasMore = true;
            
            while (hasMore && page_num <= 20) {
                const q = "reviews(input: { filters: { storefrontId: '" + vid + "' }, orderBy: { type: 'date', sort: 'desc' }, pagination: { page: " + page_num + ", size: 50 } }) { totalCount nodes { id comment { text createdAt } rating reviewer { name } title } pageInfo { hasNextPage } }";
                
                const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify({query: "query { " + q.replace(/'/g, '"') + " }"})
                });
                const d = await resp.json();
                const data = d?.data?.reviews;
                if (!data || !data.nodes) break;
                
                for (const node of data.nodes) {
                    all.push(node);
                }
                
                hasMore = data.pageInfo?.hasNextPage;
                page_num++;
                
                if (page_num === 1) {
                    console.log("Total count:", data.totalCount);
                }
            }
            
            return {total_fetched: all.length, pages: page_num - 1, sample: all.slice(0, 3)};
        }''', ids['uuid'])
        
        print(json.dumps(all_reviews, default=str)[:2000])
        
        await browser.close()

asyncio.run(main())