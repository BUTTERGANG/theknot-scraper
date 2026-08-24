"""Scrape vendor websites for package pricing data using Playwright."""
import asyncio, json, os, re
from pathlib import Path
from datetime import datetime

os.environ.setdefault('DISPLAY', ':99')
PLAYWRIGHT_BROWSERS_PATH = str(Path.home() / '.cache' / 'ms-playwright')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_PATH

BROWSER_PATH = str(Path.home() / '.cache' / 'ms-playwright' / 'chromium-1234' / 'chrome-linux64' / 'chrome')

# Target vendors: priority order (direct competitors for LA Media)
TARGETS = [
    {
        'name': 'Complete Weddings + Events Indianapolis',
        'category': 'DJ',
        'url': 'http://www.completeindy.com',
        'package_pages': ['/', '/packages', '/pricing', '/dj-packages', '/wedding-packages', '/services'],
    },
    {
        'name': 'MAC Events',
        'category': 'DJ',
        'url': 'http://maceventsindy.com/weddings',
        'package_pages': ['/', '/packages', '/pricing', '/wedding-packages'],
    },
    {
        'name': 'All in the Details',
        'category': 'COORD',
        'url': 'http://Detailsindy.com',
        'package_pages': ['/', '/packages', '/pricing', '/services', '/wedding-plans'],
    },
    {
        'name': 'Blue Belles Weddings',
        'category': 'COORD',
        'url': 'https://bluebellesweddings.com',
        'package_pages': ['/', '/packages', '/pricing', '/services', '/wedding-plans'],
    },
    {
        'name': 'Bellagala Wedding Planners',
        'category': 'COORD',
        'url': 'https://shopnational.bellagala.com/pages/indianapolis-event-planning',
        'package_pages': ['/'],
    },
    {
        'name': 'Kings Court Weddings',
        'category': 'COORD',
        'url': 'http://www.kings-court-weddings.org',
        'package_pages': ['/', '/services', '/packages', '/pricing'],
    },
    {
        'name': 'Beau & Co. Creative',
        'category': 'COORD',
        'url': 'http://beauandcocreative.com',
        'package_pages': ['/', '/services', '/packages', '/pricing'],
    },
    {
        'name': 'Royal Weddings and Events',
        'category': 'COORD',
        'url': 'https://royalweddingsco.com',
        'package_pages': ['/', '/services', '/packages', '/pricing'],
    },
    {
        'name': 'S.H.E. - Skye High Events',
        'category': 'COORD',
        'url': 'https://www.sheskyehighevents.com',
        'package_pages': ['/', '/services', '/packages', '/pricing'],
    },
    {
        'name': 'J2 Wedding Co.',
        'category': 'COORD',
        'url': 'http://j2weddingco.com',
        'package_pages': ['/', '/services', '/packages', '/pricing'],
    },
    {
        'name': 'IndyGigz LLC',
        'category': 'DJ',
        'url': 'http://www.indygigz.com/our-gigz.html',
        'package_pages': ['/', '/pricing', '/dj-packages', '/services'],
    },
]

async def main():
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        executable_path=BROWSER_PATH if os.path.exists(BROWSER_PATH) else None,
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
    )
    ctx = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    )
    
    packages_data = []
    
    for target in TARGETS:
        print(f"\n{'='*60}")
        print(f"TARGET: {target['name']} ({target['category']})")
        print(f"{'='*60}")
        
        vendor_packages = {
            'name': target['name'],
            'category': target['category'],
            'url': target['url'],
            'packages': [],
            'addons': [],
            'starting_prices_raw': [],
            'pages_scraped': [],
            'errors': [],
            'scraped_at': datetime.utcnow().isoformat(),
        }
        
        base_url = target['url'].rstrip('/')
        
        for page_path in target['package_pages']:
            url = f"{base_url}{page_path}"
            print(f"  Trying: {url}")
            try:
                page = await ctx.new_page()
                try:
                    resp = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(3)
                    
                    status = resp.status if resp else 0
                    title = await page.title()
                    print(f"    Status: {status}, Title: {title[:60]}")
                    
                    if status >= 400:
                        vendor_packages['pages_scraped'].append({'url': url, 'status': status, 'title': title})
                        await page.close()
                        continue
                    
                    # Extract all text content
                    text = await page.evaluate('''() => document.body.innerText''')
                    text = text[:10000] if text else ''
                    
                    # Extract visible price-like patterns
                    prices = await page.evaluate('''() => {
                        const results = [];
                        // Find price patterns
                        const body = document.body;
                        // Look for $ signs with numbers
                        const text = body.innerText;
                        const priceRegex = /\\$\\s*[\\d,]+(?:\\.[\\d]{2})?/g;
                        const matches = [...text.matchAll(priceRegex)];
                        results.push(...matches.map(m => m[0]));
                        
                        // Look for package/card elements
                        const els = document.querySelectorAll('[class*="package"], [class*="Package"], [class*="pricing"], [class*="Pricing"], [class*="plan"], [class*="Plan"], [class*="card"], [class*="tier"]');
                        const cards = [];
                        els.forEach(el => {
                            const t = el.innerText.trim();
                            if (t && t.length < 500) cards.push(t);
                        });
                        
                        return { prices: results.slice(0, 30), cards: cards.slice(0, 20) };
                    }''')
                    
                    vendor_packages['pages_scraped'].append({
                        'url': url, 'status': status, 'title': title,
                        'prices_found': prices.get('prices', [])[:15],
                        'card_count': len(prices.get('cards', [])),
                    })
                    vendor_packages['starting_prices_raw'].extend(prices.get('prices', []))
                    
                    # Look for structured JSON-LD or schema data
                    schema = await page.evaluate('''() => {
                        const results = [];
                        document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                            try {
                                const d = JSON.parse(s.textContent);
                                if (d["@type"] === "Product" || d["@type"] === "Service" || d["@type"] === "LocalBusiness") {
                                    results.push({
                                        type: d["@type"],
                                        name: d.name,
                                        offers: d.offers,
                                        priceRange: d.priceRange,
                                    });
                                }
                            } catch(e) {}
                        });
                        return results;
                    }''')
                    
                    if schema:
                        for s in schema:
                            vendor_packages['packages'].append(s)
                    
                    # Scan for links that mention pricing/packages
                    package_links = await page.evaluate('''() => {
                        const links = [];
                        document.querySelectorAll('a[href]').forEach(a => {
                            const href = a.getAttribute('href');
                            const text = a.textContent.toLowerCase().trim();
                            if (href && (text.includes('package') || text.includes('pricing') || text.includes('plan') || 
                                text.includes('price') || text.includes('tier'))) {
                                links.push({ text: a.textContent.trim(), href: href });
                            }
                        });
                        return links.slice(0, 10);
                    }''')
                    
                    if package_links:
                        print(f"    Package links found: {len(package_links)}")
                        for pl in package_links[:5]:
                            print(f"      {pl['text'][:40]:40s} -> {pl['href']}")
                    
                finally:
                    await page.close()
                    
            except Exception as e:
                vendor_packages['errors'].append(f"{url}: {type(e).__name__}")
                print(f"    Error: {type(e).__name__}")
        
        # Deduplicate prices
        seen = set()
        unique_prices = []
        for p in vendor_packages['starting_prices_raw']:
            normalized = p.replace(',', '').strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_prices.append(p)
        vendor_packages['starting_prices_raw'] = unique_prices
        
        packages_data.append(vendor_packages)
        
        # Summary
        print(f"  Packages found: {len(vendor_packages['packages'])}")
        print(f"  Prices found: {vendor_packages['starting_prices_raw'][:10]}")
    
    await browser.close()
    await pw.stop()
    
    # Save
    output_dir = Path.home() / 'wedding-pricing-data'
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = output_dir / f'vendor_packages_{ts}.json'
    with open(out_path, 'w') as f:
        json.dump(packages_data, f, indent=2, default=str)
    print(f"\n\nSaved to {out_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for v in packages_data:
        prices = v['starting_prices_raw'][:8]
        num_pages = len(v['pages_scraped'])
        print(f"  {v['name'][:35]:35s} | pages={num_pages} | prices={len(v['starting_prices_raw'])} | {prices}")

asyncio.run(main())