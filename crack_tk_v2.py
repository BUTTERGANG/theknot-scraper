"""
Correct TheKnot review query — select subfields of ratings
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
            return { vendorId: raw.vendorId || '', uuid: raw.id || '' };
        }''')
        vid = ids['vendorId']
        print(f"Vendor ID: {vid}")
        
        def try_q(field_str):
            return page.evaluate('''async function(f) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 3000)};
                    return {ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', field_str)
        
        # 1. review(id:) with ratings subfields
        q = 'review(id: "%s") { id ratings { id score } createdAt }' % vid
        print(f"\n=== {q[:80]} ===")
        r = await try_q(q)
        print(json.dumps(r, default=str)[:1000])
        
        # 2. Try with text
        q = 'review(id: "%s") { id text title createdAt ratings { id score } }' % vid
        r = await try_q(q)
        print(f"\n=== With text ===")
        print(json.dumps(r, default=str)[:1000])
        
        # 3. Try with reviewer
        q = 'review(id: "%s") { id text title createdAt ratings { id score category } reviewer { id name } }' % vid
        r = await try_q(q)
        print(f"\n=== With reviewer ===")
        print(json.dumps(r, default=str)[:1000])
        
        # 4. Try all possible fields
        q = 'review(id: "%s") { id text title createdAt ratings { id score category } reviewer { id name } vendorReply { text createdAt } }' % vid
        r = await try_q(q)
        print(f"\n=== Full ===")
        print(json.dumps(r, default=str)[:1500])
        
        # 5. Explore all query fields
        print("\n=== All query fields ===")
        r = await try_q('{ __schema { queryType { fields { name } } } }')
        if r.get('ok'):
            data = json.loads(r['data'])
            fields = data.get('__schema', {}).get('queryType', {}).get('fields', [])
            print("  " + ", ".join(f['name'] for f in fields if 'review' in f['name'].lower()))
        
        # 6. Check Review type
        print("\n=== Review type ===")
        r = await try_q('{ __type(name: "Review") { fields { name type { name kind } } } }')
        print(json.dumps(r, default=str)[:1000])
        
        # 7. Check ReviewRating type
        print("\n=== ReviewRating type ===")
        r = await try_q('{ __type(name: "ReviewRating") { fields { name type { name kind } } } }')
        print(json.dumps(r, default=str)[:1000])
        
        await browser.close()

asyncio.run(main())