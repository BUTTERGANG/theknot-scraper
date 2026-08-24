"""
TheKnot: __type query needs proper syntax. Try introspection differently.
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
        
        # Try introspection with proper syntax
        print("=== Introspection ===")
        r = await page.evaluate('''async function(sid) {
            try {
                const q = {
                    query: "query Introspection { __schema { types { name kind fields { name type { name kind ofType { name } } } } } }"
                };
                const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify(q)
                });
                const d = await resp.json();
                
                if (!d.data || !d.data.__schema) return JSON.stringify(d).slice(0, 500);
                
                const types = d.data.__schema.types;
                const results = {};
                for (const t of types) {
                    if (["Review", "Comment", "Reviewer", "ReviewRating", "PaginatedReview"].includes(t.name)) {
                        results[t.name] = (t.fields || []).map(function(f) {
                            var tn = f.type && (f.type.name || (f.type.ofType && f.type.ofType.name)) || "?";
                            return f.name + ": " + tn;
                        });
                    }
                }
                return JSON.stringify(results, null, 2);
            } catch(e) { return "ERROR: " + e.message; }
        }''', storefront_id)
        print(r[:3000])
        
        await browser.close()

asyncio.run(main())