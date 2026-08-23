"""
TheKnot deep page analysis - find vendor data and API endpoints
"""
import asyncio, json, os
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def main():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        page = await context.new_page()
        
        # Track XHR/fetch requests
        api_calls = []
        async def track_request(req):
            url = req.url
            if any(x in url for x in ['api', 'graphql', 'vendor', 'search', 'listings', 'recommend']):
                api_calls.append({'url': url[:200], 'method': req.method, 'resource': req.resource_type})
        
        page.on('request', track_request)
        
        # Go to photographer search
        print("=== DEEP PAGE ANALYSIS ===")
        print("Loading Indianapolis photographers...")
        await page.goto(
            'https://www.theknot.com/marketplace/wedding-photographers-indianapolis-in',
            wait_until='domcontentloaded',
            timeout=30000
        )
        await asyncio.sleep(5)  # Let JS execute
        
        # Capture what the page actually looks like
        print(f"\nURL: {page.url}")
        print(f"Title: {await page.title()}")
        
        # Get full HTML for analysis
        html = await page.content()
        
        # Save it
        out_dir = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')
        out_dir.mkdir(exist_ok=True)
        with open(out_dir / 'theknot_deep_analysis.html', 'w') as f:
            f.write(html)
        print(f"\nHTML saved: {len(html):,} chars")
        
        # --- ANALYSIS ---
        
        # 1. Check API calls intercepted
        print(f"\n=== API CALLS DETECTED ({len(api_calls)}) ===")
        for c in api_calls[:15]:
            print(f"  {c['method']} {c['url']}")
        if len(api_calls) > 15:
            print(f"  ... and {len(api_calls)-15} more")
        
        # 2. Find all data attributes / storefront data / window.__INITIAL_STATE__
        print("\n=== CLIENT-SIDE DATA ===")
        js_vars = []
        for var_name in ['__INITIAL_STATE__', '__NEXT_DATA__', '__NUXT__', '__REACT_QUERY_STATE__',
                         '__APOLLO_STATE__', 'window.__DATA__', '__PRELOADED_STATE__']:
            try:
                val = await page.evaluate(f'typeof {var_name} !== "undefined" ? "EXISTS(" + JSON.stringify({var_name}).substring(0,200) + "...)" : "NOT FOUND"')
                print(f"  {var_name}: {val}")
            except Exception as e:
                print(f"  {var_name}: Error - {e}")
        
        # 3. Check for __NEXT_DATA__ specifically (Next.js sites)
        try:
            next_data = await page.evaluate('''() => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent.substring(0, 300) : 'NOT FOUND';
            }''')
            print(f"\n  __NEXT_DATA__ element: {next_data}")
        except Exception as e:
            print(f"\n  __NEXT_DATA__ element error: {e}")
        
        # 4. Look for storefronts or vendor cards in DOM
        print("\n=== VENDOR DOM ELEMENTS ===")
        for selector in [
            '[class*="vendor"]', '[class*="Vendor"]', '[class*="card"]', '[class*="Card"]',
            '[class*="storefront"]', '[class*="Storefront"]', '[class*="result"]',
            '[class*="listing"]', '[class*="search-result"]', '[data-testid]',
            'article', '[role="listitem"]', 'li[class]',
        ]:
            try:
                els = await page.query_selector_all(selector)
                if els:
                    # Get first one's classes/text
                    first_classes = await els[0].get_attribute('class') if els else ''
                    first_text = (await els[0].inner_text())[:80] if els else ''
                    print(f"  {selector}: {len(els)} found")
                    if first_classes:
                        print(f"    class: {first_classes[:120]}")
                    if first_text:
                        print(f"    text: {first_text}")
                    if len(els) > 1:
                        next_text = (await els[1].inner_text())[:80] if els[1] else ''
                        if next_text:
                            print(f"    text2: {next_text}")
            except Exception as e:
                print(f"  {selector}: error - {e}")
        
        # 5. Look for GraphQL endpoints in HTML
        print("\n=== GRAPHQL/API ENDPOINTS IN HTML ===")
        import re
        endpoints = set()
        for pattern in [
            r'https?://[^"\']*(?:api|graphql|vendor|search|listing|recommend)[^"\']*',
            r'https?://[^"\']*\.theknot\.com[^"\']*',
        ]:
            for m in re.finditer(pattern, html):
                endpoints.add(m.group()[:180])
        for ep in sorted(list(endpoints))[:20]:
            print(f"  {ep}")
        
        # 6. Check what the visible page text actually shows  
        print("\n=== VISIBLE PAGE TEXT (body) ===")
        try:
            body_text = await page.inner_text('body')
            print(f"  Body text length: {len(body_text):,} chars")
            # Show first 1000 chars
            print(f"  Preview: {body_text[:1000]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        await browser.close()
        print("\n=== ANALYSIS COMPLETE ===")

asyncio.run(main())