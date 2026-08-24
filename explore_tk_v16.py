"""
TheKnot: Fix field names — ratings not rating, Comment has no text, Reviewer has no name
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
        
        storefront_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""')
        print("Storefront ID: %s" % storefront_id)
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) {
                        return {ok: true, data: JSON.stringify(d.data).slice(0, 5000)};
                    }
                    const msgs2 = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "no data";
                    return {ok: false, error: msgs2};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        # Explore sub-types
        print("=== Exploring types ===")
        for t in ['Review', 'Comment', 'Reviewer']:
            q = '__type(name: "%s") { fields { name type { name kind ofType { name } } } }' % t
            r = await try_q(q)
            if r.get('ok'):
                data = json.loads(r['data'])
                fields = data.get('__type', {}).get('fields', [])
                print("\n  %s:" % t)
                for f in fields:
                    tn = f['type'].get('name') or (f['type'].get('ofType') or {}).get('name') or str(f['type'])
                    print(f"    {f['name']}: {tn}")
        
        await browser.close()

asyncio.run(main())