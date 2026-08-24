"""
Fix: TheKnot search results use 'reviewsCount' not 'review_count'
Check the raw field names from __INITIAL_STATE__
"""
import asyncio, json, os
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def check_fields():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Load a search page
        await page.goto('https://www.theknot.com/marketplace/wedding-djs-chicago-il',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        state = await page.evaluate('() => window.__INITIAL_STATE__')
        
        if state:
            vendors_list = state.get('search', {}).get('vendors', [])
            print(f"Vendors on page: {len(vendors_list)}")
            
            if vendors_list:
                v = vendors_list[0]
                print(f"\nFirst vendor: {v.get('name')}")
                print(f"All keys with review/rating/star:")
                for k, val in sorted(v.items()):
                    if any(x in k.lower() for x in ['review', 'rating', 'star', 'count']):
                        print(f"  {k}: {val}")
                
                # Show all non-null fields
                print(f"\nAll populated fields:")
                for k, val in sorted(v.items()):
                    if val is not None and val != '' and val != [] and val != {} and val != 0 and val != False:
                        s = json.dumps(val, default=str)
                        if len(s) > 100:
                            s = s[:100] + '...'
                        print(f"  {k}: {s}")
        
        await browser.close()

asyncio.run(check_fields())