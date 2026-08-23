"""
TheKnot Production Scraper — Playwright + __INITIAL_STATE__ extraction

Extracts structured vendor data from TheKnot.com marketplace and vendor detail pages
by reading the React Redux state embedded in each page.

Usage:
  python theknot_scraper_v2.py --city "indianapolis" --category "wedding-photographers" --max 10
  python theknot_scraper_v2.py --vendor-url https://www.theknot.com/marketplace/vendor-name-city-st--12345
"""
import asyncio, json, os, re, sys, argparse, time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

BROWSER_PATH = str(Path.home() / '.cache' / 'ms-playwright' / 'chromium-1234' / 'chrome-linux64' / 'chrome')


@dataclass
class VendorProfile:
    """All vendor data we can extract"""
    marketplace_id: str = ''
    vendor_id: str = ''
    name: str = ''
    
    # Contact
    phone: str = ''
    email: str = ''
    website_url: str = ''
    display_website_url: str = ''
    service_area: str = ''
    address_city: str = ''
    address_state: str = ''
    
    # Pricing
    starting_price_range: str = ''
    starting_price_min: Optional[float] = None
    starting_price_avg: Optional[float] = None
    
    # Reviews
    review_count: int = 0
    star_rating: float = 0.0
    
    # Profile
    description: str = ''
    headline: str = ''
    ad_tier: str = ''
    vendor_tier: str = ''
    claimed_status: str = ''
    
    # Deals
    deals: list = field(default_factory=list)
    
    # Social
    facebook_url: str = ''
    instagram_username: str = ''
    pinterest_username: str = ''
    
    # Awards
    awards: list = field(default_factory=list)
    
    # Business details
    year_founded: Optional[int] = None
    team_size: Optional[int] = None
    travel_distance: Optional[int] = None
    
    # TheKnot URL
    theknot_url: str = ''
    
    # Raw state file (for debugging)
    raw_state_file: str = ''
    
    # Scrape metadata
    scraped_at: str = ''
    scrape_success: bool = False
    scrape_error: str = ''


class TheKnotScraperV2:
    """Playwright-based scraper using __INITIAL_STATE__ extraction"""
    
    CATEGORIES = {
        'wedding-photographers': 'WPH',
        'wedding-venues': 'REC',
        'wedding-planners': 'WPL',
        'wedding-florists': 'WFL',
        'wedding-caterers': 'WCA',
        'wedding-djs': 'WDJ',
        'wedding-bands': 'WBA',
        'wedding-videographers': 'WVI',
        'wedding-officiants': 'WOFF',
        'wedding-hair-makeup': 'WHM',
        'wedding-cakes': 'WCAK',
        'wedding-invitations': 'WINV',
        'wedding-rentals': 'WREN',
        'wedding-lighting': 'WLIG',
        'wedding-photobooths': 'WPHT',
        'wedding-transportation': 'WTRN',
    }
    
    def __init__(self, output_dir: str = 'output', headless: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
    
    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            executable_path=BROWSER_PATH if os.path.exists(BROWSER_PATH) else None,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox', '--disable-dev-shm-usage',
            ]
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
    
    async def _extract_initial_state(self) -> Optional[dict]:
        try:
            state = await self.page.evaluate('() => window.__INITIAL_STATE__')
            return state
        except Exception as e:
            return None
    
    def _parse_vendor_from_detail(self, state: dict, url: str) -> VendorProfile:
        """Parse vendor detail from __INITIAL_STATE__"""
        v = VendorProfile()
        v.theknot_url = url
        v.scrape_success = False
        v.scraped_at = datetime.utcnow().isoformat()
        
        if not state:
            v.scrape_error = 'No initial state found'
            return v
        
        vendor_obj = (state.get('vendor') or {}).get('vendor') or {}
        raw = (state.get('vendor') or {}).get('vendorRaw') or {}
        
        # Use raw first, fallback to vendor_obj
        src = raw if raw and raw.get('name') else vendor_obj
        
        v.marketplace_id = src.get('id', '')
        v.vendor_id = src.get('vendorId', '')
        v.name = src.get('name', '')
        
        # Contact
        phone_list = src.get('phones', []) or []
        if phone_list and isinstance(phone_list, list):
            for p in phone_list:
                if isinstance(p, dict) and p.get('number'):
                    v.phone = p['number']
                    if p.get('type') == 'PRIMARY':
                        break
        v.phone = v.phone or src.get('phone', '') or ''
        email_list = src.get('emails', [])
        if email_list and isinstance(email_list, list):
            v.email = email_list[0].get('address', '') if isinstance(email_list[0], dict) else str(email_list[0])
        v.email = v.email or src.get('email', '') or ''
        v.website_url = src.get('websiteUrl', '') or ''
        v.display_website_url = src.get('displayWebsiteUrl', '') or ''
        
        # Location
        loc = src.get('location', {}) or {}
        v.address_city = loc.get('city', '') or loc.get('address', {}).get('city', '') or ''
        v.address_state = loc.get('state', '') or loc.get('address', {}).get('state', '') or ''
        v.service_area = loc.get('serviceArea', '') or src.get('serviceArea', '') or ''
        
        # Pricing
        pricing = src.get('pricing', {}) or {}
        no_season = pricing.get('noSeason', {}) or {}
        v.starting_price_min = no_season.get('min', {}).get('value') if isinstance(no_season.get('min'), dict) else None
        v.starting_price_avg = no_season.get('average', {}).get('value') if isinstance(no_season.get('average'), dict) else None
        v.starting_price_range = vendor_obj.get('startingPriceRange', '') or ''
        
        # Reviews
        review_summary = src.get('reviewSummary', {}) or {}
        v.review_count = review_summary.get('count', 0) or src.get('reviewsCount', 0) or 0
        v.star_rating = review_summary.get('overallRating', 0.0) or vendor_obj.get('starCount', 0.0) or vendor_obj.get('stars', 0.0) or 0.0
        
        # Profile
        v.description = src.get('description', '')[:5000] or ''
        v.headline = src.get('headline', '') or ''
        v.ad_tier = src.get('adTier', '') or ''
        v.vendor_tier = src.get('vendorTier', '') or ''
        v.claimed_status = src.get('claimedStatus', '') or ''
        
        # Deals
        deals_data = src.get('deals', {}) or {}
        v.deals = deals_data.get('items', []) if isinstance(deals_data, dict) else []
        
        # Social
        social = src.get('social', {}) or src.get('socialMedia', []) or {}
        if isinstance(social, list):
            for s in social:
                code = s.get('code', '') if isinstance(s, dict) else ''
                val = s.get('value', '') if isinstance(s, dict) else ''
                if 'FBURL' in code or 'FACEBOOK' in code:
                    v.facebook_url = val
                elif 'INSTAGRAM' in code:
                    v.instagram_username = val
                elif 'PINTEREST' in code:
                    v.pinterest_username = val
        elif isinstance(social, dict):
            v.facebook_url = social.get('facebookUrl', '') or ''
            v.instagram_username = social.get('instagramUsername', '') or ''
            v.pinterest_username = social.get('pinterestUsername', '') or ''
        
        # Awards
        v.awards = src.get('awards', []) or vendor_obj.get('awards', []) or []
        
        # Org details
        org = src.get('orgDetails', {}) or {}
        v.year_founded = org.get('startYear')
        v.team_size = org.get('totalMembers')
        v.travel_distance = org.get('travelAvailability')
        
        if v.name:
            v.scrape_success = True
            # Save raw state for debugging
            raw_path = self.output_dir / f"raw_{v.vendor_id[:8] or v.marketplace_id[:8]}.json"
            with open(raw_path, 'w') as f:
                json.dump({'vendor': state.get('vendor')}, f, indent=2, default=str)
            v.raw_state_file = str(raw_path)
        
        return v
    
    def _parse_vendor_from_search(self, vendor_data: dict) -> VendorProfile:
        """Parse vendor from search results list"""
        v = VendorProfile()
        v.marketplace_id = vendor_data.get('id', '')
        v.vendor_id = vendor_data.get('vendorId', '')
        v.name = vendor_data.get('name', '')
        v.ad_tier = vendor_data.get('adTier', '')
        v.vendor_tier = vendor_data.get('vendorTier', '')
        v.claimed_status = vendor_data.get('claimedStatus', '')
        v.service_area = vendor_data.get('serviceArea', '') or ''
        
        # Location
        loc = vendor_data.get('location', {}) or {}
        v.address_city = loc.get('city', '') or ''
        v.address_state = loc.get('state', '') or ''
        
        # Pricing
        v.starting_price_range = vendor_data.get('startingPriceRange', '') or ''
        
        # Reviews
        v.review_count = vendor_data.get('reviewsCount', 0) or 0
        v.star_rating = vendor_data.get('stars', 0.0) or vendor_data.get('starCount', 0.0) or 0.0
        
        # Deals
        v.deals = vendor_data.get('deals', []) or []
        
        # Awards
        v.has_award_placeholder = vendor_data.get('hasAward', False)
        
        return v
    
    async def search_marketplace(self, city: str, category: str, state_code: str = '', max_pages: int = 1) -> list:
        """
        Search the marketplace and extract vendor listings
        Returns list of VendorProfile (basic info) with vendor URLs
        """
        # Build URL
        state_part = f"-{state_code.lower()}" if state_code else ""
        url = f"https://www.theknot.com/marketplace/{category}-{city.lower().replace(' ', '-')}{state_part}"
        
        print(f"Searching: {url}")
        await self._goto(url, wait_after=5)
        
        # Extract initial state
        state = await self._extract_initial_state()
        
        if not state:
            print("  ERROR: No __INITIAL_STATE__ found")
            return []
        
        # Get search results from state
        search = state.get('search', {})
        vendor_list = search.get('vendors', [])
        total = search.get('total', 0)
        page_info = search.get('pagination', {})
        
        print(f"  Total results: {total}")
        print(f"  Page {page_info.get('page', 1)} of {page_info.get('limit', 30)} per page (loaded {page_info.get('count', 0)})")
        print(f"  Vendors on page: {len(vendor_list)}")
        
        results = []
        for v_data in vendor_list:
            v = self._parse_vendor_from_search(v_data)
            # Build the TheKnot URL from the vendor data
            site_urls = v_data.get('siteUrls', [])
            if site_urls:
                v.theknot_url = site_urls[0].get('uri', '') if isinstance(site_urls[0], dict) else ''
            if not v.theknot_url:
                # Build from parts
                name_slug = v.name.lower().replace(' & ', '-').replace(' ', '-').replace('--', '-').replace(',', '')
                name_slug = re.sub(r'[^a-z0-9-]', '', name_slug)
                loc_slug = f"{v.address_city.lower().replace(' ', '-')}-{v.address_state.lower()}" if v.address_state else v.address_city.lower().replace(' ', '-')
                v.theknot_url = f"https://www.theknot.com/marketplace/{name_slug}-{loc_slug}-{v.marketplace_id[:8]}"
            v.scraped_at = datetime.utcnow().isoformat()
            v.scrape_success = True
            results.append(v)
        
        # Save search results
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = self.output_dir / f"search_{category}_{city}_{ts}.json"
        with open(out_path, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2, default=str)
        print(f"  Saved {len(results)} results to {out_path}")
        
        return results
    
    async def scrape_vendor_detail(self, url: str) -> Optional[VendorProfile]:
        """Scrape detailed vendor info from a vendor page"""
        print(f"\nScraping vendor: {url}")
        await self._goto(url, wait_after=4)
        
        state = await self._extract_initial_state()
        v = self._parse_vendor_from_detail(state, url)
        
        if v.scrape_success:
            print(f"  ✅ {v.name} | ${v.starting_price_min or '?'} - ${v.starting_price_avg or '?'} | {v.star_rating}★ ({v.review_count}) | {v.phone or 'no phone'} | {v.email or 'no email'}")
        else:
            print(f"  ❌ Failed: {v.scrape_error}")
        
        return v
    
    async def scrape_marketplace_and_details(
        self, city: str, category: str, state_code: str = '', max_vendors: int = 10
    ) -> list:
        """Full pipeline: search marketplace, then scrape each vendor detail"""
        vendors = await self.search_marketplace(city, category, state_code)
        
        if not vendors:
            print("  No vendors found in search results")
            return []
        
        # Limit
        vendors = vendors[:max_vendors]
        print(f"\nScraping details for {len(vendors)} vendors...")
        
        detailed = []
        for i, v in enumerate(vendors, 1):
            if v.theknot_url:
                detail = await self.scrape_vendor_detail(v.theknot_url)
                if detail:
                    detailed.append(detail)
            else:
                detailed.append(v)
            if i < len(vendors):
                await asyncio.sleep(2 + (i % 3))  # Randomish delay
        
        # Save all detailed results
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = self.output_dir / f"vendors_{category}_{city}_{ts}.json"
        with open(out_path, 'w') as f:
            json.dump([asdict(r) for r in detailed], f, indent=2, default=str)
        print(f"\nSaved {len(detailed)} detailed vendors to {out_path}")
        
        return detailed


async def main():
    parser = argparse.ArgumentParser(description='TheKnot Scraper v2')
    parser.add_argument('--city', default='indianapolis', help='City to search')
    parser.add_argument('--category', default='wedding-photographers', help='Vendor category slug')
    parser.add_argument('--state', default='in', help='State code')
    parser.add_argument('--max', type=int, default=10, help='Max vendors to scrape')
    parser.add_argument('--vendor-url', help='Single vendor URL to scrape')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    parser.add_argument('--output', default='output', help='Output directory')
    args = parser.parse_args()
    
    scraper = TheKnotScraperV2(output_dir=args.output, headless=args.headless)
    
    print("=" * 60)
    print("THEKNOT SCRAPER v2")
    print("=" * 60)
    
    try:
        await scraper.start()
        
        if args.vendor_url:
            v = await scraper.scrape_vendor_detail(args.vendor_url)
            if v:
                print(f"\n=== RESULT ===")
                for k, val in asdict(v).items():
                    if val:
                        s = str(val)
                        if len(s) > 300:
                            s = s[:300] + '...'
                        print(f"  {k}: {s}")
        else:
            results = await scraper.scrape_marketplace_and_details(
                city=args.city,
                category=args.category,
                state_code=args.state,
                max_vendors=args.max
            )
            print(f"\n=== SUMMARY ===")
            success = sum(1 for r in results if r.scrape_success)
            print(f"  Total: {len(results)}")
            print(f"  Successful: {success}")
            print(f"  Failed: {len(results) - success}")
    finally:
        await scraper.stop()

if __name__ == '__main__':
    asyncio.run(main())