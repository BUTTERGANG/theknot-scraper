"""
Final GraphQL probe — try 'reviews' and 'summaryReviews' fields
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def probe():
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
        display_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.displayId || ""')
        print(f"Vendor ID: {vendor_id} / Display: {display_id}")
        
        # Try various query names
        for field_name in ['reviews', 'summaryReviews', 'vendorReviews', 'getReviews']:
            result = await page.evaluate('''async ({vid, field}) => {
                const queryStr = `query Test($vendorId: ID!, $first: Int!, $after: String) {
                    ${field}(vendorId: $vendorId, first: $first, after: $after) {
                        edges { node { id rating text } }
                    }
                }`;
                const q = { operationName: "Test", variables: { vendorId: vid, first: 3, after: null }, query: queryStr };
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method:"POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify(q)
                    });
                    const d = await r.json();
                    if (d.data) {
                        const keys = Object.keys(d.data);
                        const edges = d.data[keys[0]]?.edges || [];
                        return {field, ok: true, edges: edges.length, data: JSON.stringify(d.data).slice(0, 500)};
                    }
                    return {field, ok: false, error: d.errors?.[0]?.message || 'no data'};
                } catch(e) { return {field, ok: false, error: e.message}; }
            }''', {'vid': vendor_id, 'field': field_name})
            print(f"  {field_name}: {json.dumps(result, default=str)[:300]}")
        
        # Try with accountId instead
        account_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.accountId || ""')
        print(f"\nAccount ID: {account_id}")

        # Introspect to find the right arguments for reviews/summaryReviews
        print("\n=== GraphQL Introspection ===")
        schema = await page.evaluate('''async () => {
            const q = {
                query: `{ __schema { types { name fields { name args { name type { name kind } } } } } }`
            };
            const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                method:"POST",
                headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                body: JSON.stringify(q)
            });
            const d = await r.json();
            const types = d?.data?.__schema?.types || [];
            // Find Query type
            const queryType = types.find(t => t.name === "Query");
            if (queryType) {
                return queryType.fields
                    .filter(f => f.name.includes("review") || f.name.includes("Review"))
                    .map(f => ({name: f.name, args: f.args.map(a => ({name: a.name, type: a.type?.name}))}));
            }
            return null;
        }''')
        print(f"  Review-related query fields: {json.dumps(schema, default=str)[:1000]}")
        
        await browser.close()

asyncio.run(probe())