"""
Explore Zola __NEXT_DATA__ structure to find all vendor data paths
"""
import json, os
from pathlib import Path

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

import asyncio
from playwright.async_api import async_playwright

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Search page
        print("Fetching Zola search page...")
        await page.goto('https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        # Get __NEXT_DATA__
        next_data = await page.evaluate('''() => {
            const el = document.getElementById("__NEXT_DATA__");
            return el ? JSON.parse(el.textContent) : null;
        }''')
        
        if not next_data:
            print("No __NEXT_DATA__")
            await browser.close()
            return
        
        print(f"__NEXT_DATA__ keys: {list(next_data.keys())}")
        
        # Explore paths
        props = next_data.get('props', {})
        page_props = props.get('pageProps', {})
        print(f"\npageProps keys: {list(page_props.keys())}")
        
        # Look for vendor-related keys
        for k in page_props:
            v = page_props[k]
            if isinstance(v, dict):
                print(f"\n--- pageProps.{k} (dict, {len(v)} keys: {list(v.keys())[:10]}) ---")
                # Show first key's type
                first_key = list(v.keys())[0] if v else None
                if first_key:
                    fv = v[first_key]
                    print(f"  {first_key}: {type(fv).__name__}")
                    if isinstance(fv, dict):
                        print(f"  keys: {list(fv.keys())[:10]}")
                        # Check for vendors
                        for sk in fv:
                            if 'vendor' in sk.lower() or 'result' in sk.lower():
                                sv = fv[sk]
                                print(f"    {sk}: {type(sv).__name__} len={len(sv) if hasattr(sv, '__len__') else 'N/A'}")
            elif isinstance(v, list):
                print(f"\n--- pageProps.{k} (list[{len(v)}]) ---")
                if v:
                    print(f"  first item type: {type(v[0]).__name__}")
                    if isinstance(v[0], dict):
                        print(f"  keys: {list(v[0].keys())[:20]}")
        
        # Also save for analysis
        with open(out / 'zola_next_data.json', 'w') as f:
            json.dump(next_data, f, indent=2, default=str)
        print(f"\nFull __NEXT_DATA__ saved ({len(json.dumps(next_data, default=str)):,} chars)")
        
        # Now try a vendor detail page
        print("\n--- VENDOR DETAIL PAGE ---")
        # Get first vendor's URL from page
        vendor_link = await page.evaluate('''() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.href && a.href.includes('/wedding-vendors/wedding-photographers/') 
                    && !a.href.includes('/search/') && !a.href.includes('/find/')) {
                    return a.href;
                }
            }
            return null;
        }''')
        
        if vendor_link:
            print(f"Navigating to: {vendor_link}")
            await page.goto(vendor_link, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            detail_next_data = await page.evaluate('''() => {
                const el = document.getElementById("__NEXT_DATA__");
                return el ? JSON.parse(el.textContent) : null;
            }''')
            
            if detail_next_data:
                with open(out / 'zola_vendor_detail_next_data.json', 'w') as f:
                    json.dump(detail_next_data, f, indent=2, default=str)
                print(f"Vendor detail __NEXT_DATA__ saved")
                
                # Explore
                dp = detail_next_data.get('props', {}).get('pageProps', {})
                print(f"Detail pageProps keys: {list(dp.keys())[:15]}")
                for k in dp:
                    v = dp[k]
                    s = json.dumps(v, default=str)
                    if len(s) < 500 and v:
                        print(f"  {k}: {s[:300]}")
        
        await browser.close()

asyncio.run(explore())