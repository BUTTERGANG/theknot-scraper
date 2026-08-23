"""
WeddingWire Scraper — Playwright + server-rendered HTML parsing

WeddingWire uses traditional server-rendered HTML (not Next.js),
with infinite scroll pagination via XHR.

Usage:
  python weddingwire_scraper.py --category "wedding-photographers" --max 5
"""
import asyncio, json, os, re, sys, argparse, time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')


@dataclass
class WWVendorProfile:
    name: str = ''
    biz_id: str = ''
    biz_url: str = ''
    rating: float = 0.0
    review_count: int = 0
    starting_price: str = ''
    location: str = ''
    phone: str = ''
    website: str = ''
    description: str = ''
    category: str = ''
    badges: list = field(default_factory=list)
    source_url: str = ''
    scraped_at: str = ''
    scrape_success: bool = False


class WeddingWireScraper:
    BASE = 'https://www.weddingwire.com'
    
    def __init__(self, output_dir: str = 'output', headless: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser = None
    
    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        
        browser_path = str(Path.home() / '.cache' / 'ms-playwright' / 'chromium-1234' / 'chrome-linux64' / 'chrome')
        
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            executable_path=browser_path if os.path.exists(browser_path) else None,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await self.context.new_page()
    
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_pw') and self._pw:
            await self._pw.stop()
    
    async def _goto(self, url: str, wait_after: int = 3):
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(wait_after)
    
    async def search_vendors(self, category: str, location: str = '') -> list:
        """Search WeddingWire for vendors by category and optional location"""
        url = f"{self.BASE}/{category}" if not location else f"{self.BASE}/{category}?location={location}"
        
        print(f"Searching WeddingWire: {url}")
        await self._goto(url, wait_after=5)
        
        vendors = []
        
        # Extract vendor data from server-rendered HTML
        # WeddingWire renders vendor cards in the initial HTML
        try:
            # Get all vendor-related elements
            vendor_cards = await self.page.query_selector_all('[class*="vendor"], [class*="listing"], [data-vendor-id], article')
            
            # Also try extracting via JS - look for vendor data in page
            vendor_data = await self.page.evaluate('''() => {
                const results = [];
                
                // 1. Parse ItemList JSON-LD (has vendor list with ratings)
                document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                    try {
                        const data = JSON.parse(s.textContent);
                        if (data["@type"] === "ItemList" && data.itemListElement) {
                            data.itemListElement.forEach(item => {
                                if (item.item) {
                                    const biz = item.item;
                                    results.push({
                                        name: biz.name || "",
                                        rating: biz.aggregateRating?.ratingValue ? parseFloat(biz.aggregateRating.ratingValue) : 0,
                                        reviewCount: biz.aggregateRating?.reviewCount ? parseInt(biz.aggregateRating.reviewCount) : 0,
                                        price: biz.priceRange || "",
                                        url: biz["@id"] || biz.url || "",
                                        description: biz.description || "",
                                        image: biz.image || "",
                                    });
                                }
                            });
                        }
                    } catch(e) {}
                });
                
                // 2. Parse application/json for vendor listing data
                document.querySelectorAll('script[type="application/json"]').forEach(s => {
                    try {
                        const data = JSON.parse(s.textContent);
                        if (data.nItems || data.vendors) {
                            results.push({_jsonData: JSON.stringify(data).substring(0, 1000)});
                        }
                    } catch(e) {}
                });
                
                // 3. Scan for vendor links as fallback
                if (results.length === 0) {
                    document.querySelectorAll('a[href*="/biz/"]').forEach(a => {
                        const name = a.textContent.trim();
                        if (name && name.length > 2 && name.length < 100) {
                            // Don't add dups
                            if (!results.some(r => r.name === name)) {
                                results.push({name, url: a.href, rating: 0, reviewCount: 0, price: ""});
                            }
                        }
                    });
                }
                
                return results;
            }''')
            
            for v in vendor_data:
                if v.get('name') and len(v['name']) > 2:
                    profile = WWVendorProfile()
                    profile.name = v['name']
                    profile.biz_url = v.get('url', '')
                    profile.starting_price = v.get('price', '')
                    profile.rating = v.get('rating', 0.0)
                    profile.review_count = v.get('reviewCount', 0)
                    profile.description = v.get('description', '')[:2000]
                    profile.source_url = url
                    profile.scraped_at = datetime.utcnow().isoformat()
                    profile.scrape_success = True
                    vendors.append(profile)
            
        except Exception as e:
            print(f"  Error extracting vendors: {e}")
        
        # Deduplicate
        seen = set()
        unique = []
        for v in vendors:
            key = v.name.lower().strip()
            if key not in seen and len(key) > 2:
                seen.add(key)
                unique.append(v)
        
        print(f"  Found {len(unique)} vendors (from {len(vendors)} raw)")
        
        # Save
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = self.output_dir / f"ww_search_{category.replace('/', '_')}_{ts}.json"
        with open(out, 'w') as f:
            json.dump([asdict(v) for v in unique], f, indent=2, default=str)
        print(f"  Saved to {out}")
        
        return unique


async def main():
    parser = argparse.ArgumentParser(description='WeddingWire Scraper')
    parser.add_argument('--category', default='wedding-photographers')
    parser.add_argument('--location', default='')
    parser.add_argument('--output', default='output')
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    
    scraper = WeddingWireScraper(output_dir=args.output, headless=args.headless)
    
    print("=" * 60)
    print("WEDDINGWIRE SCRAPER")
    print("=" * 60)
    
    try:
        await scraper.start()
        vendors = await scraper.search_vendors(args.category, args.location)
        print(f"\nTotal: {len(vendors)} vendors")
    finally:
        await scraper.stop()

if __name__ == '__main__':
    asyncio.run(main())