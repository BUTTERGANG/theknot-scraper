"""
Crack TheKnot reviews GraphQL — find correct query + arguments
"""
import os, asyncio, json, re
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def crack():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Load a vendor page
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        vendor_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.vendorId || ""')
        display_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.displayId || ""')
        vendor_uuid = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""')
        location_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.locationId || ""')
        print(f"Vendor: {vendor_id}")
        print(f"Display: {display_id}")
        print(f"UUID: {vendor_uuid}")
        print(f"Location: {location_id}")
        
        # 1. Introspect the reviews-api to find the args for 'reviews' field
        print("\n=== Step 1: Introspect reviews field schema ===")
        schema_info = await page.evaluate('''async () => {
            const q = {
                query: `{
                    __schema {
                        types {
                            name
                            fields {
                                name
                                args {
                                    name
                                    type { name kind ofType { name } }
                                }
                            }
                        }
                    }
                }`
            };
            const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                method:"POST",
                headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                body: JSON.stringify(q)
            });
            const d = await r.json();
            const types = d?.data?.__schema?.types || [];
            
            // Find 'reviews' and 'summaryReviews' field definitions
            const results = {};
            for (const t of types) {
                if (t.name === "Query" && t.fields) {
                    results.Query_fields = t.fields.map(f => ({
                        name: f.name,
                        args: f.args.map(a => ({name: a.name, type: a.type?.name || a.type?.ofType?.name}))
                    }));
                }
                // Also find ReviewConnection/Review types
                if (t.name && (t.name.includes("Review") || t.name.includes("review"))) {
                    results[t.name] = t.fields ? t.fields.map(f => ({
                        name: f.name,
                        type: f.type?.name || f.type?.ofType?.name
                    })) : "no fields";
                }
            }
            return results;
        }''')
        
        print(f"Query fields with 'review':")
        if schema_info:
            for qf in schema_info.get('Query_fields', []):
                if 'review' in qf['name'].lower():
                    print(f"  {qf['name']}({qf['args']})")
        
        print(f"\nAll review-related types:")
        for k, v in schema_info.items():
            if k != 'Query_fields':
                print(f"  {k}: {type(v).__name__}")
                if isinstance(v, list):
                    for f in v[:10]:
                        print(f"    {f['name']}: {f['type']}")
        
        # 2. Search JS bundles for GraphQL fragments containing review patterns
        print("\n=== Step 2: Search page source for review query patterns ===")
        patterns = await page.evaluate('''() => {
            const html = document.documentElement.outerHTML;
            const results = [];
            
            // Look for GraphQL query strings
            const gqlMatch = html.match(/query\s+\w+[^}]{0,500}review[^}]{0,500}/gi);
            if (gqlMatch) results.push({type: "query", matches: gqlMatch.slice(0, 5)});
            
            // Look for operation names
            const opMatch = html.match(/["']operationName["']\s*:\s*["']\w*review\w*["']/gi);
            if (opMatch) results.push({type: "operationName", matches: opMatch.slice(0, 5)});
            
            // Look for vendorId usage in API calls
            const apiMatch = html.match(/vendorId[^,}]{0,100}/g);
            if (apiMatch) results.push({type: "vendorId_usage", matches: apiMatch.slice(0, 5)});
            
            // Look for /v1/ or /api/ paths with reviews
            const urlMatch = html.match(/["'][^"']*review[^"']*["']/g);
            if (urlMatch) results.push({type: "review_urls", matches: urlMatch.slice(0, 5)});
            
            // Check all bundled script tags for review-related code
            const scripts = document.querySelectorAll('script[src*="bundle"], script[src*="chunk"], script[src*="main"]');
            results.push({type: "bundles_with_review", count: scripts.length});
            
            return results;
        }''')
        print(json.dumps(patterns, default=str)[:2000])
        
        # 3. Try the marketplace-api GraphQL endpoint with different auth
        print("\n=== Step 3: Try marketplace-api GraphQL ===")
        # Get cookies first
        cookies = await page.evaluate('() => document.cookie')
        print(f"Cookies: {cookies[:200]}")
        
        marketplace = await page.evaluate('''async ({vid, cookie}) => {
            const q = {
                query: `query GetReviewSummary($vendorId: ID!) {
                    reviewSummary(vendorId: $vendorId) {
                        count
                        overallRating
                        reviews {
                            id
                            rating
                            title
                            text
                            createdAt
                            reviewer { name }
                        }
                    }
                }`,
                variables: { vendorId: vid }
            };
            try {
                const r = await fetch("https://prod-marketplace-api.localsolutions.theknot.com/graphql", {
                    method: "POST",
                    headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                    credentials: "include",
                    body: JSON.stringify(q)
                });
                const d = await r.json();
                return JSON.stringify(d).slice(0, 3000);
            } catch(e) { return "ERROR: " + e.message; }
        }''', {'vid': vendor_id, 'cookie': cookies})
        print(f"marketplace-api result: {marketplace[:2000]}")
        
        # 4. Guess common arg patterns
        print("\n=== Step 4: Test common arg patterns ===")
        for arg_name in ['storefrontId', 'locationId', 'id', 'displayId', 'accountId', 'vendorUuid']:
            result = await page.evaluate('''async ({vid, arg}) => {
                const q = {
                    query: `query Test($id: ID!, $first: Int!) {
                        reviews(${arg}: $id, first: $first) {
                            edges { node { id rating text } }
                        }
                    }`,
                    variables: { id: vid, first: 2 }
                };
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify(q)
                    });
                    const d = await r.json();
                    if (d.data) return {arg, ok: true, data: JSON.stringify(d.data).slice(0, 300)};
                    return {arg, ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {arg, ok: false, error: e.message}; }
            }''', {'vid': vendor_id, 'arg': arg_name})
            print(f"  reviews({arg_name}): {json.dumps(result, default=str)[:200]}")
        
        # 5. Try the vrm section in Redux state 
        print("\n=== Step 5: Check VRM section for review data pattern ===")
        vrm_info = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            if (!s || !s.vrm) return null;
            const vrm = s.vrm;
            return {
                keys: Object.keys(vrm),
                isOpen: vrm.isOpen,
                factorsCount: (vrm.factors || []).length,
                factors: JSON.stringify(vrm.factors).slice(0, 300),
                similarVendors: JSON.stringify(vrm.similarVendors).slice(0, 300),
            };
        }''')
        print(f"VRM: {json.dumps(vrm_info, default=str)[:500]}")
        
        await browser.close()

asyncio.run(crack())