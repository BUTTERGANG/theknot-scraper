"""
Explore TheKnot review type field names by trial and error
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
        
        vid = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.vendorId || ""')
        print(f"Vendor ID: {vid}")
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 3000)};
                    return {ok: false, error: (d.errors?.[0]?.message || "no data").slice(0, 200)};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        # First: what fields does review have?
        print("\n=== Review base fields ===")
        for f in ['id', 'overallRating', 'averageRating', 'ratingValue', 'starRating',
                 'reviewCount', 'totalCount', 'total', 'count',
                 'summary', 'description', 'body', 'comment',
                 'rating', 'score']:
            q = 'review(id: "%s") { %s }' % (vid, f)
            r = await try_q(q)
            if r.get('ok'):
                print(f"  ✅ {f}: {r['data'][:200]}")
            elif 'Cannot query' not in str(r.get('error', '')):
                print(f"  ⚠️ {f}: {r.get('error', '')[:100]}")
        
        # Try ratings with various subfields
        print("\n=== ratings subfields ===")
        q = 'review(id: "%s") { ratings { id } }' % vid
        r = await try_q(q)
        print(f"  ratings.id: {json.dumps(r, default=str)[:300]}")
        
        if r.get('ok'):
            for f in ['value', 'name', 'category', 'label', 'count', 'percent',
                     'max', 'min', 'average', 'stars', 'score', 'type', 'key']:
                q2 = 'review(id: "%s") { ratings { %s } }' % (vid, f)
                r2 = await try_q(q2)
                if r2.get('ok'):
                    print(f"  ✅ ratings.{f}: {r2['data'][:200]}")
                elif 'Cannot query' not in str(r2.get('error', '')):
                    print(f"  ⚠️ ratings.{f}: {r2.get('error', '')[:100]}")
        
        # Check if review is a list or has edges
        print("\n=== Edge/connection patterns ===")
        for q in [
            'reviews(first: 3) { edges { node { id } } }',
            'reviewConnection(first: 3) { edges { node { id } } }',
            'allReviews(first: 3) { edges { node { id } } }',
            'vendorReviews(first: 3) { edges { node { id } } }',
        ]:
            r = await try_q(q)
            if r.get('ok'):
                print(f"  ✅ {q[:50]}: {r['data'][:200]}")
            elif 'Cannot query' not in str(r.get('error', '')):
                print(f"  ⚠️ {q[:50]}: {r.get('error', '')[:100]}")
        
        # The actual review data: what is review(id:) returning?
        q = 'review(id: "%s") { id overallRating reviewCount ratings { id value name } }' % vid
        r = await try_q(q)
        print(f"\n=== Best guess for review data ===")
        print(json.dumps(r, default=str)[:1000])
        
        await browser.close()

asyncio.run(main())