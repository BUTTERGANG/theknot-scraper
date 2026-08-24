"""
Find TheKnot's actual review GraphQL query by searching webpack bundles + network intercept
"""
import os, asyncio, json, re
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def find_query():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Capture ALL network requests (not just response bodies)
        all_requests = []
        async def on_request(req):
            all_requests.append({
                'url': req.url[:180],
                'method': req.method,
                'type': req.resource_type,
            })
        page.on('request', on_request)
        
        # Intercept POST bodies to capture GraphQL queries
        gql_queries = []
        async def on_response(resp):
            url = resp.url
            req = resp.request
            
            # Capture GraphQL POST bodies
            if req.method == 'POST' and ('graphql' in url.lower() or 'api' in url.lower()):
                try:
                    body = req.post_data
                    if body and 'query' in body:
                        gql_queries.append({
                            'url': url[:160],
                            'body_preview': body[:3000],
                            'status': resp.status,
                        })
                except: pass
            
            # Also capture review-related GET responses from theknot.com
            if 'review' in url.lower() and 'response.status' in str(dir(resp)):
                try:
                    body = await resp.text()
                    if len(body) > 100 and 'review' in body.lower():
                        gql_queries.append({
                            'url': url[:160],
                            'response_preview': body[:2000],
                            'status': resp.status,
                        })
                except: pass
        
        page.on('response', on_response)
        
        # Load vendor page
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Try clicking to trigger reviews load - find the review count
        # Click the stars or review count
        await page.evaluate('''() => {
            // Try clicking the 2625 reviews link
            const elements = document.querySelectorAll('a, span, button, [role="button"]');
            for (const el of elements) {
                const t = (el.textContent || '').toLowerCase().trim();
                if (t.includes('2625') || t.includes('review') && (t.includes('see') || t.includes('all'))) {
                    el.click();
                    console.log('CLICKED:', t);
                    return;
                }
            }
            // Try clicking the rating section
            const ratings = document.querySelectorAll('[class*="rating"], [data-testid*="rating"]');
            for (const r of ratings) {
                if (r.textContent && r.textContent.includes('review')) {
                    r.click();
                    return;
                }
            }
        }''')
        await asyncio.sleep(3)
        
        # Check if a new tab/window opened
        pages = ctx.pages
        if len(pages) > 1:
            print(f"New page opened: {pages[-1].url}")
            page = pages[-1]
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(3)
        
        # Print intercepted GraphQL queries
        print(f"\n=== Intercepted GraphQL queries ({len(gql_queries)}) ===")
        for g in gql_queries:
            print(f"\n  [{g['status']}] {g['url']}")
            print(f"  Body: {g.get('body_preview', '')[:1000]}")
            if g.get('response_preview'):
                print(f"  Response: {g['response_preview'][:1000]}")
        
        # Search all bundle JS for review-related query strings
        print(f"\n=== Searching bundles for review GraphQL queries ===")
        found_patterns = await page.evaluate('''() => {
            const results = [];
            
            // Get all inline scripts
            document.querySelectorAll('script').forEach(s => {
                const text = s.textContent || '';
                
                // Look for GraphQL query strings mentioning review
                const matches = text.match(/query\s+\w+[^}]{0,800}review[^}]{0,800}/gi);
                if (matches) {
                    results.push({type: 'inline', samples: matches.slice(0, 3)});
                }
                
                // Look for operation names 
                const ops = text.match(/["']operationName["']\s*:\s*["']([^"']+)["']/g);
                if (ops) {
                    const reviewOps = ops.filter(o => o.toLowerCase().includes('review'));
                    if (reviewOps.length > 0) results.push({type: 'ops', samples: reviewOps.slice(0, 5)});
                }
            });
            
            // Also check external scripts if possible
            document.querySelectorAll('script[src]').forEach(s => {
                const src = s.src;
                if (src.includes('vendor') || src.includes('main') || src.includes('bundle')) {
                    results.push({type: 'external_script', src: src.slice(0, 120)});
                }
            });
            
            return results;
        }''')
        
        print(f"Found {len(found_patterns)} results:")
        for p in found_patterns:
            print(f"  {p.get('type', '?')}: {json.dumps(p.get('samples', p.get('src', '')), default=str)[:500]}")
        
        # Finally, try loading a bundle file directly and extract review queries
        print(f"\n=== Fetching bundle files for review queries ===")
        bundle_srcs = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('script[src*="monorepo"][src*="bundle"]'))
                .map(s => s.src)
                .filter(s => !s.includes('vendors-') && (s.includes('main') || s.includes('Marketplace')))
                .slice(0, 5);
        }''')
        
        for bs in bundle_srcs:
            print(f"\n  Bundle: {bs.split('/')[-1][:80]}")
            try:
                await page.goto(bs, wait_until='domcontentloaded', timeout=15000)
                body = await page.content()
                # Search for review-related graphql patterns
                matches = re.findall(r'query\s+\w{0,50}\s*\([^)]{0,200}\)\s*\{[^}]{0,500}review[^}]{0,500}', body)
                if matches:
                    for m in matches[:3]:
                        print(f"    Query: {m[:200]}...")
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"\n=== Network requests summary ===")
        graphql_reqs = [r for r in all_requests if 'graphql' in r['url'].lower() or 'api' in r['url'].lower()]
        for r in graphql_reqs[:10]:
            print(f"  [{r['method']}] [{r['type']}] {r['url']}")
        
        await browser.close()

asyncio.run(find_query())