"""
TheKnot reviews API cracked! Now extract full review data
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def crack_it():
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
                uuid: raw.id || '',
                vendorId: raw.vendorId || '',
                displayId: raw.displayId || '',
                accountId: raw.accountId || '',
                locationId: raw.locationId || '',
            };
        }''')
        print(f"IDs: {json.dumps(ids)}")
        
        def try_q(field_str, desc=""):
            return page.evaluate('''async function({f, d}) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: `query { ${f} }`})
                    });
                    const d2 = await r.json();
                    if (d2.data) return {d, ok: true, data: JSON.stringify(d2.data).slice(0, 2000)};
                    return {d, ok: false, error: d2.errors?.[0]?.message || "no data"};
                } catch(e) { return {d, ok: false, error: e.message}; }
            }''', {'f': field_str, 'd': desc or field_str[:60]})
        
        # Try review(id:) with correct field names
        print("\n=== review(id:) with correct fields ===")
        for vid_name in ['vendorId', 'uuid', 'displayId', 'accountId', 'locationId']:
            for vid in [ids[vid_name]]:
                if not vid: continue
                r = await try_q(f'review(id: "{vid}") {{ id ratings text createdAt title }}', f'review({vid_name}={vid[:8]})')
                print(f"  {json.dumps(r, default=str)[:300]}")
                if r.get('ok'): break
        
        # Try reviews (plural) with id
        print("\n=== reviews (plural) with id: ===")
        for vid_name in ['vendorId', 'uuid', 'displayId', 'accountId', 'locationId']:
            vid = ids[vid_name]
            if not vid: continue
            r = await try_q(f'reviews(id: "{vid}", first: 5) {{ edges {{ node {{ id ratings text createdAt }} }} }}', f'reviews({vid_name}={vid[:8]})')
            print(f"  {json.dumps(r, default=str)[:300]}")
            if r.get('ok'):
                print(f"  ✅ WORKS! Full data: {r['data'][:500]}")
                break
        
        # Once we find the working query, paginate
        if not any(r.get('ok') for r in [await try_q(f'reviews(id: "{ids[v]}", first: 5) {{ edges {{ node {{ id }} }} }}', 'test') for v in ids if ids[v]]):
            # Try with locationId as the key
            print("\n=== reviews with locationId ===")
            r = await try_q(f'reviews(id: "{ids["locationId"]}", first: 5) {{ edges {{ node {{ id ratings text }} }} }}', 'locationId')
            print(f"  {json.dumps(r, default=str)[:400]}")
        
        # Try the full pagination
        print("\n=== Full pagination ===")
        # Use the vendorId (original ID) - that's what the snippet uses
        r = await page.evaluate('''async function({vid}) {
            const fetchReviews = async (after) => {
                const q = {
                    query: `query Q($id: ID!, $first: Int!, $after: String) {
                        reviews(id: $id, first: $first, after: $after) {
                            edges { node { id ratings text createdAt title } }
                            pageInfo { hasNextPage endCursor totalCount }
                        }
                    }`,
                    variables: { id: vid, first: 50, after: after }
                };
                const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify(q)
                });
                return await resp.json();
            };
            
            let all = [];
            let cursor = null;
            let hasMore = true;
            let pages = 0;
            
            while (hasMore && pages < 10) {
                pages++;
                const d = await fetchReviews(cursor);
                const data = d?.data?.reviews;
                if (!data) break;
                
                for (const edge of data.edges) {
                    all.push(edge.node);
                }
                
                hasMore = data.pageInfo?.hasNextPage;
                cursor = data.pageInfo?.endCursor;
                if (pages === 1) {
                    return {totalCount: data.pageInfo?.totalCount, firstPageSize: data.edges.length, hasMore, sample: JSON.stringify(all.slice(0, 2)).slice(0, 1000)};
                }
            }
            return {total: all.length, pages, sample: JSON.stringify(all.slice(0, 2)).slice(0, 1000)};
        }''', {'vid': ids['vendorId']})
        print(f"  Result: {json.dumps(r, default=str)[:1000]}")
        
        await browser.close()

asyncio.run(crack_it())