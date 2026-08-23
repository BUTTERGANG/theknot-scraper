"""
Extract structured vendor data from TheKnot via __INITIAL_STATE__ and vendor detail pages
"""
import asyncio, json, os, re
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

out_dir = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')
out_dir.mkdir(exist_ok=True)

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
        
        print("=== DATA EXTRACTION ===")
        
        # --- STEP 1: Extract marketplace listing data from __INITIAL_STATE__ ---
        print("\n[1/3] Marketplace listing...")
        await page.goto(
            'https://www.theknot.com/marketplace/wedding-photographers-indianapolis-in',
            wait_until='domcontentloaded',
            timeout=30000
        )
        await asyncio.sleep(5)
        
        # Extract INITIAL_STATE
        initial_state = await page.evaluate('() => window.__INITIAL_STATE__')
        
        print(f"  __INITIAL_STATE__ keys: {list(initial_state.keys()) if initial_state else 'EMPTY'}")
        
        # Save the full state
        with open(out_dir / 'initial_state.json', 'w') as f:
            json.dump(initial_state, f, indent=2, default=str)
        is_size = len(json.dumps(initial_state, default=str))
        print(f"  Saved: {is_size:,} chars")
        
        # Extract vendor listings from state
        if initial_state and 'vendors' in initial_state:
            v_state = initial_state['vendors']
            print(f"  Vendors state: {json.dumps({k: type(v).__name__ for k,v in v_state.items()}, default=str)[:300]}")
            
            # Look for vendor list
            if 'list' in v_state:
                vendors = v_state['list']
                print(f"  Vendors in list: {len(vendors) if isinstance(vendors, list) else 'not a list'}")
                if isinstance(vendors, list) and vendors:
                    print(f"  First vendor keys: {list(vendors[0].keys()) if isinstance(vendors[0], dict) else 'not dict'}")
        
        # Try alternate paths in state
        for path in ['search', 'results', 'marketplace', 'listings']:
            if path in initial_state:
                data = initial_state[path]
                print(f"  State['{path}'] type: {type(data).__name__}")
                if isinstance(data, dict):
                    print(f"    keys: {list(data.keys())[:10]}")
        
        # --- STEP 2: Extract vendor detail page ---
        print("\n[2/3] Vendor detail page...")
        
        # Get first vendor URL from the page
        vendor_link = await page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*="/marketplace/"][href*="--"]');
            if (links.length > 0) {
                return links[0].href;
            }
            // Try alternative - find the "Vendor Details" buttons
            const buttons = document.querySelectorAll('[class*="vendor"] a, [class*="vendor"] button');
            for (const btn of buttons) {
                const href = btn.getAttribute('href') || btn.closest('a')?.getAttribute('href');
                if (href && href.includes('/marketplace/')) {
                    return href.startsWith('http') ? href : 'https://www.theknot.com' + href;
                }
            }
            return null;
        }''')
        
        if vendor_link:
            print(f"  Vendor URL: {vendor_link}")
            await page.goto(vendor_link, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # Get detail page state
            detail_state = await page.evaluate('() => window.__INITIAL_STATE__')
            
            print(f"  Detail state keys: {list(detail_state.keys()) if detail_state else 'NONE'}")
            
            if detail_state:
                with open(out_dir / 'vendor_detail_state.json', 'w') as f:
                    json.dump(detail_state, f, indent=2, default=str)
                print(f"  Detail state saved: {len(json.dumps(detail_state, default=str)):,} chars")
            
            # Extract visible vendor info
            vendor_info = await page.evaluate('''() => {
                const info = {};
                // Business name
                const h1 = document.querySelector('h1');
                if (h1) info.name = h1.innerText;
                
                // Price
                const priceEls = document.querySelectorAll('[class*="price"], [class*="Price"]');
                info.prices = Array.from(priceEls).slice(0,5).map(el => el.innerText.trim());
                
                // Description / about
                const about = document.querySelector('[class*="about"], [class*="About"], [class*="description"]');
                if (about) info.about = about.innerText.substring(0, 500);
                
                // Packages
                const packages = document.querySelectorAll('[class*="package"], [class*="Package"]');
                info.package_count = packages.length;
                info.packages = Array.from(packages).slice(0,5).map(p => p.innerText.substring(0, 200));
                
                // Contact info
                const contact = document.querySelector('[class*="contact"], [class*="Contact"], [data-testid*="contact"]');
                if (contact) info.contact = contact.innerText.substring(0, 300);
                
                // Website links
                info.links = Array.from(document.querySelectorAll('a[href*="http"]'))
                    .filter(a => !a.href.includes('theknot.com') && !a.href.includes('xogrp.com'))
                    .slice(0,5)
                    .map(a => ({text: a.innerText.trim(), href: a.href}));
                
                return info;
            }''')
            
            print(f"\n  Vendor Info:")
            for k, v in vendor_info.items():
                if isinstance(v, list) and len(v) > 3:
                    print(f"    {k}: {v[:3]} (total {len(v)})")
                else:
                    print(f"    {k}: {v}")
        
        else:
            print("  No vendor URL found on page")
        
        # --- STEP 3: Extract from HTML saved file ---
        print("\n[3/3] Extracting from saved HTML...")
        
        # Read the HTML saved earlier and extract structured data
        html_path = out_dir / 'theknot_deep_analysis.html'
        if html_path.exists():
            html = html_path.read_text()
            
            # Find JSON-LD
            jsonld_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
            jsonld_blocks = jsonld_pattern.findall(html)
            print(f"  JSON-LD blocks in HTML: {len(jsonld_blocks)}")
            for i, block in enumerate(jsonld_blocks[:3]):
                try:
                    data = json.loads(block)
                    print(f"    Block {i+1}: {json.dumps(data, default=str)[:200]}")
                except:
                    print(f"    Block {i+1}: (parse error) {block[:200]}")
            
            # Find __INITIAL_STATE__ in HTML (it might be a script tag)
            state_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', re.DOTALL)
            state_match = state_pattern.search(html)
            if state_match:
                print(f"  __INITIAL_STATE__ found in HTML (regex)")
        
        await browser.close()
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Files saved in: {out_dir}")

asyncio.run(main())