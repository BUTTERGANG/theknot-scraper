"""
TheKnot: reviews takes ReviewsInput! — explore PaginatedReview + ReviewsInput
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
            return { vendorId: raw.vendorId || '', uuid: raw.id || '', name: raw.name || '' };
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
                    return {ok: false, error: (d.errors?.[0]?.message || "no data").slice(0, 200)};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        print(f"Vendor: {ids['name']} / ID: {ids['vendorId']}")
        
        # PaginatedReview fields
        print("\n=== PaginatedReview fields ===")
        for f in ['items { id }', 'nodes { id }', 'edges { node { id } }', 'results { id }',
                 'reviews { id }', 'data { id }', 'entries { id }', 'list { id }',
                 'totalCount', 'total', 'count', 'pageInfo { hasNextPage }',
                 'items { comment { text } rating }']:
            q = 'reviews { %s }' % f
            r = await try_q(q)
            if r.get('ok'):
                print(f"  ✅ {f}: {r['data'][:300]}")
            elif 'Cannot query' not in str(r.get('error', '')):
                print(f"  ⚠️ {f}: {r.get('error', '')[:100]}")
        
        # ReviewsInput exploration via GraphQL error messages
        print("\n=== ReviewsInput field exploration ===")
        # Try various shapes of input
        for input_shape in [
            '{vendorId: "%s"}' % ids['vendorId'],
            '{revieweeId: "%s"}' % ids['vendorId'],
            '{accountId: "%s"}' % ids['vendorId'],
            '{storefrontId: "%s"}' % ids['vendorId'],
            '{id: "%s"}' % ids['vendorId'],
        ]:
            q = 'reviews(input: %s) { items { id } }' % input_shape
            r = await try_q(q)
            if r.get('ok'):
                print(f"  ✅ {input_shape[:40]}: {r['data'][:300]}")
            # The error message will tell us what field is expected
            elif 'Unknown field' in str(r.get('error', '')):
                print(f"  {input_shape[:40]}: {r.get('error', '')}")
        
        # Try empty input
        q = 'reviews(input: {}) { items { id } }'
        r = await try_q(q)
        print(f"\n  empty input: {json.dumps(r, default=str)[:300]}")
        
        # Try the review (singular) with full field exploration
        print("\n=== Full review object fields ===")
        for f in ['comment { text }', 'rating', 'ratings { id value }', 'reviewer { id name }',
                 'reviewee { id name }', 'reviewerId', 'revieweeId', 'score', 'status',
                 'createdAt', 'updatedAt', 'title', 'summary']:
            # This won't return data (wrong ID) but will tell us valid fields
            q = 'review(id: "test-id") { %s }' % f
            r = await try_q(q)
            if 'Cannot query' not in str(r.get('error', '')):
                print(f"  {f}: {r.get('error', '')[:100]}")
        
        await browser.close()

asyncio.run(main())