"""
Extract TheKnot review query from page's webpack modules at runtime
Also try the reviews-api with different arg names
"""
import os, asyncio, json, re
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def extract():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Get vendor IDs
        ids = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            if (!s || !s.vendor) return {};
            const raw = s.vendor.vendorRaw || s.vendor.vendor || {};
            return {
                id: raw.id || '',
                vendorId: raw.vendorId || '',
                displayId: raw.displayId || '',
                accountId: raw.accountId || '',
                locationId: (raw.location || {}).id || '',
                name: raw.name || '',
            };
        }''')
        print(f"IDs: {json.dumps(ids, default=str)}")
        
        # Search webpack module cache for review-related query strings
        print("\n=== Search webpack for review queries ===")
        found = await page.evaluate('''() => {
            const results = [];
            
            // Search __webpack_modules__
            try {
                const modules = Object.values(webpackJsonp || []);
                // Check if webpack modules are accessible
                if (typeof __webpack_modules__ !== 'undefined') {
                    results.push("webpack_modules found: " + Object.keys(__webpack_modules__).length + " modules");
                }
            } catch(e) {}
            
            // Search the webpage's own JS context for GraphQL query strings
            // Look for query patterns in the page's global scope
            const scripts = document.querySelectorAll('script:not([src])');
            let fullText = '';
            scripts.forEach(s => { fullText += (s.textContent || '') + '\\n'; });
            
            // Find graphql query patterns with review
            const queryPat = /query\\s+\\w*Review\\w*\\s*\\([^)]*\\)\\s*\\{[^}]{0,500}review[^}]{0,500}/gi;
            let m;
            while ((m = queryPat.exec(fullText)) !== null) {
                results.push({type: 'query', text: m[0].slice(0, 500)});
            }
            
            // Find operationName Review
            const opPat = /operationName["']\\s*:\\s*["'][^"']*Review[^"']*["']/gi;
            while ((m = opPat.exec(fullText)) !== null) {
                results.push({type: 'opName', text: m[0]});
            }
            
            // Find gql tagged template literals with review
            const gqlPat = /gql`[^`]{0,2000}`/g;
            while ((m = gqlPat.exec(fullText)) !== null) {
                if (m[0].toLowerCase().includes('review')) {
                    results.push({type: 'gql', text: m[0].slice(0, 600)});
                }
            }
            
            return results;
        }''')
        print(f"Found {len(found)} patterns:")
        for f in found[:10]:
            print(f"  [{f.get('type', '?')}] {f.get('text', '')[:200]}")
        
        # Try the reviews endpoint with different argument names  
        print("\n=== Try more argument patterns ===")
        print(f"Vendor name: {ids.get('name')}")
        
        # The most likely arguments based on common GraphQL patterns
        for arg_name in ['vendorUuid', 'storefrontUuid', 'accountUuid', 'uuid', 'key', 'slug', 'code', 'marketCode']:
            val = ids.get('id', '')
            if arg_name == 'marketCode': val = '198'
            
            result = await page.evaluate('''async function({fn, val, name}) {
                // Build query string dynamically
                const queryStr = `query Test { ${fn}(${name}: "${val}", first: 3) { edges { node { id rating text } } } }`;
                const q = { query: queryStr };
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                        body: JSON.stringify(q)
                    });
                    const d = await r.json();
                    if (d.data) return {fn, name, ok: true, data: JSON.stringify(d.data).slice(0, 300)};
                    return {fn, name, ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {fn, name, ok: false, error: e.message}; }
            }''', {'fn': 'reviews', 'val': ids.get('id', ''), 'name': arg_name})
            print(f"  reviews({arg_name}: id): {json.dumps(result, default=str)[:200]}")
            
            # Also try with summaryReviews
            if arg_name in ['vendorUuid', 'storefrontUuid', 'uuid']:
                result2 = await page.evaluate('''async function({fn, val, name}) {
                    const queryStr = `query Test { ${fn}(${name}: "${val}") { count overallRating } }`;
                    const q = { query: queryStr };
                    try {
                        const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                            method: "POST", headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                            body: JSON.stringify(q)
                        });
                        const d = await r.json();
                        if (d.data) return {fn, name, ok: true, data: JSON.stringify(d.data).slice(0, 300)};
                        return {fn, name, ok: false, error: d.errors?.[0]?.message || "no data"};
                    } catch(e) { return {fn, name, ok: false, error: e.message}; }
                }''', {'fn': 'summaryReviews', 'val': ids.get('id', ''), 'name': arg_name})
                print(f"  summaryReviews({arg_name}): {json.dumps(result2, default=str)[:200]}")
        
        # Try with no argument at all (sometimes reviews is a connection)
        print("\n=== Try connection-based queries ===")
        for field in ['vendor { reviews { edges { node { id } } } }',
                      'storefront { reviews { edges { node { id } } } }',
                      'account { reviews { edges { node { id } } } }']:
            result = await page.evaluate('''async function({field}) {
                const q = { query: `query { ${field} }` };
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                        body: JSON.stringify(q)
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data).slice(0, 300)};
                    return {ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', {'field': field})
            if result.get('ok'):
                print(f"  {field[:50]}: {json.dumps(result, default=str)[:300]}")
        
        # Try the marketplace-api endpoint with proper auth
        print("\n=== Try marketplace-api with auth ===")
        market_result = await page.evaluate('''async function() {
            try {
                const r = await fetch("https://prod-marketplace-api.localsolutions.theknot.com/graphql", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    credentials: "include",
                    body: JSON.stringify({query: "query { __typename }"})
                });
                const d = await r.json();
                return JSON.stringify(d).slice(0, 500);
            } catch(e) { return "ERROR: " + e.message; }
        }''')
        print(f"  Result: {market_result[:500]}")
        
        await browser.close()

asyncio.run(extract())