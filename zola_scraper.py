"""
Zola Scraper — Playwright + __NEXT_DATA__ extraction

Extracts structured vendor data from Zola.com wedding vendor pages.
Zola uses Next.js with __NEXT_DATA__ embedded in the page.

Usage:
  python zola_scraper.py --city "new-york" --state "ny" --category "wedding-photographers" --max 5
"""
import asyncio, json, os, re, sys, argparse, time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')


@dataclass
class ZolaVendorProfile:
    vendor_id: str = ''
    name: str = ''
    slug: str = ''
    phone: str = ''
    website_url: str = ''
    email: str = ''
    city: str = ''
    state: str = ''
    price_tier: str = ''
    starting_price: str = ''
    description: str = ''
    review_count: int = 0
    star_rating: float = 0.0
    categories: list = field(default_factory=list)
    images: list = field(default_factory=list)
    source_url: str = ''
    scraped_at: str = ''
    scrape_success: bool = False
    scrape_error: str = ''


class ZolaScraper:
    BASE = 'https://www.zola.com'
    
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
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            locale='en-US',
        )
        self.page = await self.context.new_page()
    
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_pw') and self._pw:
            await self._pw.stop()
    
    async def _goto(self, url: str, wait_after: int = 3):
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(wait_after)
    
    async def _extract_next_data(self) -> Optional[dict]:
        """Extract __NEXT_DATA__ from the page"""
        try:
            next_data = await self.page.evaluate(
                '() => { const el = document.getElementById("__NEXT_DATA__"); '
                'return el ? JSON.parse(el.textContent) : null; }'
            )
            return next_data
        except Exception as e:
            return None
    
    def _parse_vendors_from_next_data(self, next_data: dict) -> list:
        """Parse vendor listings from __NEXT_DATA__"""
        results = []
        
        # __NEXT_DATA__ structure varies by page type.
        # Search results: props -> pageProps -> searchResults -> vendors
        # OR: props -> pageProps -> vendors
        # OR: props -> pageProps -> initialData -> vendors
        
        props = next_data.get('props', {}) or {}
        page_props = props.get('pageProps', {}) or {}
        
        # Try different paths
        candidates = []
        
        # Path 1: pageProps.searchResults.vendors
        sr = page_props.get('searchResults', {})
        vendors_list = sr.get('vendors', [])
        if vendors_list:
            candidates.append(vendors_list)
            total = sr.get('totalHits', 0)
        
        # Path 2: pageProps.vendorSearchData.vendorSearch
        vsd = page_props.get('vendorSearchData', {}).get('vendorSearch', {})
        if vsd:
            v = vsd.get('vendors', [])
            if v: candidates.append(v)
        
        # Path 3: pageProps.adjacentVendors (for detail pages)  
        adj = page_props.get('adjacentVendors', [])
        if adj: candidates.append(adj)
        
        # Parse all candidates
        seen_ids = set()
        for vendor_list in candidates:
            if not isinstance(vendor_list, list):
                continue
            for v_data in vendor_list:
                if not isinstance(v_data, dict):
                    continue
                
                vid = v_data.get('id', '') or v_data.get('vendorId', '') or v_data.get('slug', '')
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                
                profile = ZolaVendorProfile()
                profile.vendor_id = vid
                profile.name = v_data.get('name', '') or ''
                profile.slug = v_data.get('slug', '') or ''
                profile.phone = v_data.get('phone', '') or ''  # Only on detail pages
                
                # Website/social (detail pages have social.web)
                social = v_data.get('social', {})
                profile.website_url = social.get('web', '') if isinstance(social, dict) else ''
                profile.website_url = profile.website_url or v_data.get('websiteUrl', '') or ''
                
                # Location
                profile.city = v_data.get('city', '') or v_data.get('address', {}).get('city', '') or ''
                profile.state = v_data.get('stateProvince', '') or v_data.get('address', {}).get('stateProvince', '') or ''
                
                # Pricing - startingPriceCents (search results have cents)
                sp_cents = v_data.get('startingPriceCents', 0) or 0
                if sp_cents:
                    profile.starting_price = f"${sp_cents/100:.0f}"
                # startingPrice (detail pages have dollars)
                sp = v_data.get('startingPrice', 0) or 0
                if sp and not profile.starting_price:
                    profile.starting_price = f"${sp:.0f}"
                # prices array fallback
                prices_arr = v_data.get('prices', [])
                if prices_arr and isinstance(prices_arr, list) and not profile.starting_price:
                    for p_item in prices_arr:
                        if isinstance(p_item, dict):
                            mc = p_item.get('minCents', 0) or p_item.get('minCents', 0) or 0
                            if mc:
                                profile.starting_price = f"${mc/100:.0f}"
                                break
                profile.price_tier = v_data.get('priceTier', '') or 0
                
                # Reviews
                profile.review_count = v_data.get('reviewCount', 0) or v_data.get('reviewsCount', 0) or 0
                profile.star_rating = v_data.get('averageReviewsRate', 0.0) or v_data.get('starRating', 0.0) or 0.0
                
                # Categories
                cats = v_data.get('categories', []) or []
                profile.categories = [c.get('name', '') if isinstance(c, dict) else str(c) for c in cats]
                
                # Images
                photos = v_data.get('photos', []) or v_data.get('images', []) or []
                profile.images = [p.get('url', '') if isinstance(p, dict) else str(p) for p in photos[:5]]
                
                profile.scrape_success = bool(profile.name)
                
                results.append(profile)
        
        return results
    
    def _build_vendor_url(self, v: ZolaVendorProfile, category: str) -> str:
        if v.slug:
            return f"{self.BASE}/wedding-vendors/{category}/{v.slug}"
        return ''
    
    async def search_vendors(self, city: str, state: str, category: str) -> list:
        """Search Zola marketplace for vendors"""
        url = f"{self.BASE}/wedding-vendors/search/{city.lower().replace(' ', '-')}-{state.lower()}--{category}"
        print(f"Searching Zola: {url}")
        
        await self._goto(url, wait_after=5)
        
        next_data = await self._extract_next_data()
        if not next_data:
            print("  ❌ No __NEXT_DATA__ found")
            return []
        
        vendors = self._parse_vendors_from_next_data(next_data)
        print(f"  Found {len(vendors)} vendors")
        
        # Save
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = self.output_dir / f"zola_search_{category}_{city}_{ts}.json"
        with open(out, 'w') as f:
            json.dump([asdict(v) for v in vendors], f, indent=2, default=str)
        print(f"  Saved to {out}")
        
        return vendors
    
    async def scrape_vendor_detail(self, url: str) -> Optional[ZolaVendorProfile]:
        """Scrape single vendor detail page"""
        await self._goto(url, wait_after=4)
        
        next_data = await self._extract_next_data()
        if not next_data:
            print(f"  ❌ No data for {url}")
            return None
        
        vendors = self._parse_vendors_from_next_data(next_data)
        if vendors:
            v = vendors[0]
            v.source_url = url
            v.scraped_at = datetime.utcnow().isoformat()
            print(f"  ✅ {v.name} | {v.star_rating}★ ({v.review_count}) | {v.phone or 'no phone'} | {v.starting_price or v.price_tier or 'no price'}")
            return v
        return None


async def main():
    parser = argparse.ArgumentParser(description='Zola Scraper')
    parser.add_argument('--city', default='new-york')
    parser.add_argument('--state', default='ny')
    parser.add_argument('--category', default='wedding-photographers')
    parser.add_argument('--max', type=int, default=10)
    parser.add_argument('--output', default='output')
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    
    scraper = ZolaScraper(output_dir=args.output, headless=args.headless)
    
    print("=" * 60)
    print("ZOLA SCRAPER")
    print("=" * 60)
    
    try:
        await scraper.start()
        vendors = await scraper.search_vendors(args.city, args.state, args.category)
        print(f"\nTotal: {len(vendors)} vendors")
        success = sum(1 for v in vendors if v.scrape_success)
        print(f"Successful: {success}")
    finally:
        await scraper.stop()

if __name__ == '__main__':
    asyncio.run(main())