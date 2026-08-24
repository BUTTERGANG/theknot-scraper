"""
TheKnot: get full error messages for enum suggestions
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
        
        def try_q_full(f):
            """Get full error messages"""
            return page.evaluate('''async function(f2) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + f2 + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 2000)};
                    const msg = d.errors ? d.errors.map(e => e.message).join("; ") : "no data";
                    return {ok: false, error: msg};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', f)
        
        # Get full error messages for the closest matches
        print("\n=== Full enum error messages ===")
        for type_val in ['RATING_DESC', 'RATING_ASC', 'DATE_ASC', 'DATE', 'REVIEW_DATE_ASC', 'REVIEW_DATE_DESC']:
            for sort_val in ['ASC', 'DESC']:
                q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: %s, sort: %s }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, type_val, sort_val)
                r = await try_q_full(q)
                if r.get('ok'):
                    print("  OK type=%s sort=%s" % (type_val, sort_val))
                    print("  Result: %s" % r['data'][:300])
                    break
                else:
                    err = r.get('error', '')
                    if 'does not exist' in err and 'Did you mean' in err:
                        print("  type=%s sort=%s: %s" % (type_val, sort_val, err))
                    continue

        # Try completly different naming for the enum  
        print("\n=== Different enum naming patterns ===")
        for type_val in ['REVIEW_DATE_DESC', 'REVIEW_DATE_ASC', 'SORT_BY_DATE_DESC', 'SORT_BY_DATE_ACS',
                        'RECENT', 'MOST_RECENT', 'HELPFUL', 'MOST_HELPFUL',
                        'CREATED', 'UPDATED', 'RATING', 'DATE_REVIEW',
                        'REVIEW_DATE', 'LAST_UPDATED', 'MOST_RECENT_REVIEW']:
            q = 'reviews(input: { filters: { vendorId: "%s" }, orderBy: { type: %s, sort: ASC }, pagination: { pageSize: 5, page: 1 } }) { items { id } totalCount }' % (vendor_id, type_val)
            r = await try_q_full(q)
            if r.get('ok'):
                print("  OK type=%s: %s" % (type_val, r['data'][:300]))
                break
            else:
                err = r.get('error', '')
                if 'does not exist' in err:
                    if 'Did you mean' in err:
                        # Show what it suggests
                        print("  type=%s: %s" % (type_val[:20], err))
                    else:
                        pass  # Just wrong value, no suggestion
        
        await browser.close()

asyncio.run(main())