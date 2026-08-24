"""
TheKnot: Introspection disabled. Use trial-and-error to find field names.
Comment has no text — try body/content/description. Rating -> ratings. Reviewer name.
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
        
        def try_q(f):
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 5000)};
                    const msgs = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "";
                    return {ok: false, error: msgs};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        base = 'reviews(input: { filters: { storefrontId: "%s" }, orderBy: { type: date, sort: desc }, pagination: { page: 1, size: 3 } })' % storefront_id
        
        # Find Comment fields
        print("=== Comment fields ===")
        for cf in ['body', 'content', 'description', 'message', 'text_content', 'value', 'raw']:
            q = base + ' { nodes { comment { id %s } } }' % cf
            r = await try_q(q)
            if r.get('ok'):
                print("  OK comment.%s: %s" % (cf, r['data'][:300]))
            elif 'Cannot query' not in r.get('error', ''):
                print("  ? comment.%s: %s" % (cf, r.get('error', '')[:100]))
        
        # Find ReviewRating fields
        print("\n=== Ratings fields ===")
        for rf in ['value', 'score', 'name', 'category', 'type', 'label', 'key', 'level', 'stars', 'points']:
            q = base + ' { nodes { id ratings { %s } } }' % rf
            r = await try_q(q)
            if r.get('ok'):
                print("  OK rating.%s: %s" % (rf, r['data'][:300]))
            elif 'Cannot query' not in r.get('error', ''):
                print("  ? rating.%s: %s" % (rf, r.get('error', '')[:100]))
        
        # Find Reviewer fields
        print("\n=== Reviewer fields ===")
        for rf in ['displayName', 'username', 'firstName', 'lastName', 'email', 'id', 'userId', 'profile']:
            q = base + ' { nodes { reviewer { id %s } } }' % rf
            r = await try_q(q)
            if r.get('ok'):
                print("  OK reviewer.%s: %s" % (rf, r['data'][:300]))
            elif 'Cannot query' not in r.get('error', ''):
                print("  ? reviewer.%s: %s" % (rf, r.get('error', '')[:100]))
        
        # Try full query with whatever works
        # First try just id + createdAt + title
        q = base + ' { totalCount nodes { id createdAt title } }'
        r = await try_q(q)
        print("\n=== Base review (no comment/rating) ===")
        print("  %s" % json.dumps(r, default=str)[:500])
        
        await browser.close()

asyncio.run(main())