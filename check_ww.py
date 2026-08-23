"""
Check WeddingWire and Zola output structure, fix extraction
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# Zola latest
zl = sorted(out.glob('zola_search_wedding-photographers_new-york_20260823_230206.json'))
if zl:
    with open(zl[-1]) as f:
        data = json.load(f)
    print(f"ZOLA latest: type={type(data).__name__}")
    if isinstance(data, dict):
        print(f"  keys: {list(data.keys())}")
    elif isinstance(data, list):
        print(f"  count: {len(data)}")
        if data:
            print(f"  first keys: {list(data[0].keys())}")
            for k, val in sorted(data[0].items()):
                if val:
                    s = json.dumps(val, default=str)[:150]
                    print(f"    {k}: {s}")

# Check WeddingWire raw page
print("\n=== WEDDINGWIRE RAW ANALYSIS ===")

# Look at what the WeddingWire page actually contains
import os, asyncio
os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def analyze_ww():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        await page.goto('https://www.weddingwire.com/wedding-photographers', 
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        content = await page.content()
        print(f"HTML: {len(content):,} chars")
        
        # Save
        with open(out / 'ww_raw.html', 'w') as f:
            f.write(content)
        print("Saved to ww_raw.html")
        
        # Find vendor data patterns
        html = content[:200000]  # First 200K
        
        patterns = [
            'biz/', 'vendor', 'price', 'rating', '"@type"', 'LocalBusiness',
            '__NEXT_DATA__', '__INITIAL_STATE__', '__APOLLO_STATE__',
            'data-hypernova', 'window.__',
        ]
        
        for pat in patterns:
            count = html.count(pat)
            if count > 0:
                # Show context
                idx = html.find(pat)
                context = html[max(0,idx-50):idx+100]
                print(f"  {pat}: {count} matches")
                print(f"    context: {context[:150]}")
        
        # Check for __NEXT_DATA__
        next_data_elem = await page.evaluate('() => document.getElementById("__NEXT_DATA__") ? "YES" : "NO"')
        print(f"\n  __NEXT_DATA__ element: {next_data_elem}")
        
        apollo = await page.evaluate('() => typeof window.__APOLLO_STATE__ !== "undefined" ? "YES (" + Object.keys(window.__APOLLO_STATE__).length + " keys)" : "NO"')
        print(f"  __APOLLO_STATE__: {apollo}")
        
        init = await page.evaluate('() => typeof window.__INITIAL_STATE__ !== "undefined" ? "YES" : "NO"')
        print(f"  __INITIAL_STATE__: {init}")
        
        # Check for script data-hypernova (Yelp-style)
        hypernova = await page.evaluate('() => document.querySelector("[data-hypernova-key]") ? "YES" : "NO"')
        print(f"  data-hypernova: {hypernova}")
        
        # Look for JSON data in script tags
        scripts = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('script[type="application/json"], script[type="application/ld+json"]').forEach(s => {
                results.push({type: s.type, id: s.id || "none", size: (s.textContent || "").length, preview: (s.textContent || "").substring(0, 100)});
            });
            return results;
        }''')
        print(f"\n  JSON scripts:")
        for s in scripts[:5]:
            print(f"    {s['type']} id={s['id']} size={s['size']}")
            print(f"      preview: {s['preview']}")
        
        await browser.close()

asyncio.run(analyze_ww())