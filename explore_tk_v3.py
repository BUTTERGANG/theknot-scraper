"""
TheKnot: review type has reviewee/reviewees — try querying by reviewee
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
            return {
                vendorId: raw.vendorId || '',
                uuid: raw.id || '',
                displayId: raw.displayId || '',
                accountId: raw.accountId || '',
                locationId: raw.locationId || '',
                name: raw.name || '',
            };
        }''')
        print(f"IDs: {ids}")
        
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
        
        # Try reviewee-based queries
        print("\n=== Reviewee-based queries ===")
        for arg_name in ['revieweeId', 'reviewee', 'revieweeId']:
            for vid_key in ['vendorId', 'uuid', 'accountId', 'locationId', 'displayId']:
                val = ids[vid_key]
                if not val: continue
                q = 'reviews(%s: "%s") { id }' % (arg_name, val)
                r = await try_q(q)
                if r.get('ok'):
                    print(f"  ✅ reviews({arg_name}: {vid_key}): {r['data'][:200]}")
                elif 'Unknown argument' not in str(r.get('error', '')):
                    print(f"  ⚠️ reviews({arg_name}: {vid_key}): {r.get('error', '')[:100]}")
        
        # Try the review object with reviewee filter
        # reviews takes no args? Let's try it bare
        print("\n=== Bare reviews ===")
        q = 'reviews { id }'
        r = await try_q(q)
        print(f"  reviews: {json.dumps(r, default=str)[:300]}")
        
        # Try review with reviewee
        q = 'reviews(revieweeId: "%s") { id comment { text } rating }' % ids['vendorId']
        r = await try_q(q)
        print(f"  reviews(revieweeId): {json.dumps(r, default=str)[:500]}")
        
        # Try the comment subfields
        q = 'reviews(revieweeId: "%s") { id review { comment { text } } }' % ids['vendorId']
        r = await try_q(q)
        print(f"  reviews.review.comment: {json.dumps(r, default=str)[:500]}")
        
        # Try all possible arg variations
        print("\n=== All reviews arg variations ===")
        for arg_name in ['revieweeId', 'where', 'filter', 'input', 'reviewee', 'accountId', 'locationId']:
            for vid_key in ['vendorId', 'uuid', 'accountId', 'locationId']:
                val = ids[vid_key]
                if not val: continue
                for fmt in ['"%s"', '%s']:
                    actual_val = fmt % val if fmt == '%s' else fmt % val
                    # Skip non-numeric for %s format
                    if fmt == '%s' and not val.isdigit():
                        continue
                    q = 'reviews(%s: %s) { id }' % (arg_name, actual_val)
                    r = await try_q(q)
                    if r.get('ok'):
                        print(f"  ✅ reviews({arg_name}: {actual_val[:20]}): {r['data'][:200]}")
                    elif 'Unknown argument' not in str(r.get('error', '')):
                        print(f"  ⚠️ reviews({arg_name}: {actual_val[:20]}): {r.get('error', '')[:100]}")
        
        # Check if there's a vendor query that has reviews nested
        print("\n=== Nested vendor -> reviews ===")
        q = 'vendor(id: "%s") { reviews { id } }' % ids['vendorId']
        r = await try_q(q)
        print(f"  vendor.reviews: {json.dumps(r, default=str)[:300]}")
        
        q = 'storefront(id: "%s") { reviews { id } }' % ids['uuid']
        r = await try_q(q)
        print(f"  storefront.reviews: {json.dumps(r, default=str)[:300]}")
        
        # Try the marketplace-api endpoint (the one that already works) with reviews
        print("\n=== marketplace-api reviews ===")
        r = await page.evaluate('''async function() {
            const q = { query: "query { reviewSummary(vendorId: \\"92f20231-8fe9-4243-acab-1d9869a0565d\\") { count overallRating } }" };
            try {
                const resp = await fetch("https://prod-marketplace-api.localsolutions.theknot.com/graphql", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    credentials: "include",
                    body: JSON.stringify(q)
                });
                const d = await resp.json();
                return JSON.stringify(d).slice(0, 1000);
            } catch(e) { return "ERROR: " + e.message; }
        }''')
        print(f"  Result: {r[:500]}")
        
        await browser.close()

asyncio.run(main())