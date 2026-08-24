""""
wedding_pricing_scraper.py — Wedding Pricing Comparison Scraper

Scrapes DJ/MC, wedding coordination, and photobooth vendor pricing from
TheKnot, Zola, and WeddingWire for a target market.

Outputs structured pricing data with tier classification to:
  ~/wedding-pricing-data/pricing_latest.json  (combined)
  ~/wedding-pricing-data/pricing_latest.csv   (CSV)
  ~/wedding-pricing-data/pricing_YYYY-MM-DD_HHMM.json  (dated archive)

Usage:
  python wedding_pricing_scraper.py --city indianapolis --state in
  python wedding_pricing_scraper.py --city indianapolis --state in --max-vendors 20
  python wedding_pricing_scraper.py --verify-only  # Check existing data
"""

import asyncio, json, os, re, sys, argparse, csv, time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ.setdefault('DISPLAY', ':99')
PLAYWRIGHT_BROWSERS_PATH = str(Path.home() / '.cache' / 'ms-playwright')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_PATH

BROWSER_PATH = str(Path.home() / '.cache' / 'ms-playwright' / 'chromium-1234' / 'chrome-linux64' / 'chrome')

# ── Data schema ────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    # TheKnot slug -> (display name, short code)
    'wedding-djs': ('DJ / MC', 'DJ'),
    'wedding-planners': ('Wedding Coordinator', 'COORD'),
}
# Zola categories
ZOLA_CATEGORIES = {
    'wedding-djs': 'wedding-djs',
    'wedding-planners': 'wedding-planners',
    'wedding-photobooths': 'wedding-photobooths',
}
# WeddingWire categories
WW_CATEGORIES = {
    'wedding-djs': 'wedding-djs',
    'wedding-planners': 'wedding-planners',
    'wedding-photobooths': 'photo-booth-rentals',
}

TIER_THRESHOLDS = {
    'DJ': {'budget': 1200, 'mid': 2500},  # <1200 budget, 1200-2500 mid, >2500 premium
    'COORD': {'budget': 1500, 'mid': 3500},
    'PHOTOBOOTH': {'budget': 400, 'mid': 900},
}


@dataclass
class PricingVendor:
    """Unified vendor record with pricing data."""
    # Identity
    source: str = ''  # theknot, zola, weddingwire
    source_url: str = ''
    vendor_id: str = ''
    name: str = ''
    category: str = ''  # DJ, COORD, PHOTOBOOTH
    category_detail: str = ''  # e.g. 'DJ / MC'
    
    # Contact
    phone: str = ''
    email: str = ''
    website_url: str = ''
    
    # Location
    city: str = ''
    state: str = ''
    service_area: str = ''
    
    # Pricing (from marketplace)
    starting_price_min: Optional[float] = None
    starting_price_avg: Optional[float] = None
    starting_price_range: str = ''
    price_tier: str = ''  # budget, mid, premium (inferred)
    
    # Reputation
    star_rating: float = 0.0
    review_count: int = 0
    
    # Platform signals
    ad_tier: str = ''   # PLATINUM, GOLD, etc.
    vendor_tier: str = ''  # PREMIUM, FEATURED, STANDARD
    claimed_status: str = ''
    
    # Deals
    deal_count: int = 0
    deal_descriptions: list = field(default_factory=list)
    
    # Awards
    awards: list = field(default_factory=list)
    
    # Business details
    year_founded: Optional[int] = None
    team_size: Optional[int] = None
    
    # Season pricing (when available)
    peak_price_min: Optional[float] = None
    peak_price_avg: Optional[float] = None
    offpeak_price_min: Optional[float] = None
    offpeak_price_avg: Optional[float] = None
    
    # Description snippet
    description_snippet: str = ''
    
    # Metadata
    scraped_at: str = ''
    scrape_success: bool = False


# ── Tier classifier ─────────────────────────────────────────────────────────

def classify_tier(cat: str, price_avg: Optional[float], price_min: Optional[float]) -> str:
    """Classify vendor into budget/mid/premium based on average price."""
    thresholds = TIER_THRESHOLDS.get(cat, TIER_THRESHOLDS['DJ'])
    price = price_avg or price_min
    if price is None:
        return 'unknown'
    if price < thresholds['budget']:
        return 'budget'
    if price < thresholds['mid']:
        return 'mid'
    return 'premium'


# ── TheKnot scraper ────────────────────────────────────────────────────────

class TheKnotPricingScraper:
    """Scrape TheKnot for DJ and planner vendors with pricing."""
    
    CATEGORIES = {
        'wedding-djs': 'WDJ',
        'wedding-planners': 'WPL',
    }
    
    def __init__(self, output_dir: str, headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser = None
    
    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            executable_path=BROWSER_PATH if os.path.exists(BROWSER_PATH) else None,
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
    
    async def _goto(self, url: str, wait_after: int = 4):
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(wait_after)
    
    def _parse_vendor(self, v_data: dict, category_slug: str) -> PricingVendor:
        """Parse vendor from search results (ID, name, ad tier, URL)."""
        cat_display, cat_code = CATEGORY_MAP.get(category_slug, (category_slug, 'OTHER'))
        v = PricingVendor()
        v.source = 'theknot'
        v.category = cat_code
        v.category_detail = cat_display
        v.name = v_data.get('name', '')
        v.ad_tier = v_data.get('adTier', '')
        v.vendor_tier = v_data.get('vendorTier', '')
        v.claimed_status = v_data.get('claimedStatus', '')
        v.review_count = v_data.get('reviewsCount', 0) or 0
        v.star_rating = v_data.get('stars', 0.0) or 0.0
        v.starting_price_range = v_data.get('startingPriceRange', '') or ''
        v.vendor_id = v_data.get('vendorId', '') or v_data.get('id', '')
        
        # Awards
        v.awards = v_data.get('awards', []) or []
        
        # URL
        site_urls = v_data.get('siteUrls', [])
        if site_urls:
            v.source_url = site_urls[0].get('uri', '') if isinstance(site_urls[0], dict) else ''
        
        # Location (search results)
        loc = v_data.get('location', {}) or {}
        v.city = loc.get('city', '') or ''
        v.state = loc.get('state', '') or ''
        
        return v
    
    def _parse_detail(self, v: PricingVendor, state: dict):
        """Enrich vendor with detail page data (pricing, contact)."""
        if not state:
            return
        raw = (state.get('vendor') or {}).get('vendorRaw', {}) or {}
        vo = (state.get('vendor') or {}).get('vendor', {}) or {}
        src = raw if raw.get('name') else vo
        
        # Pricing
        pricing = src.get('pricing', {}) or {}
        for season_key, season_label in [('noSeason', None), ('peak', 'peak'), ('offPeak', 'offpeak')]:
            season = pricing.get(season_key) or {}
            if isinstance(season, dict):
                avg = season.get('average')
                mn = season.get('min')
                if season_label == 'peak':
                    v.peak_price_avg = avg.get('value') if isinstance(avg, dict) else None
                    v.peak_price_min = mn.get('value') if isinstance(mn, dict) else None
                elif season_label == 'offpeak':
                    v.offpeak_price_avg = avg.get('value') if isinstance(avg, dict) else None
                    v.offpeak_price_min = mn.get('value') if isinstance(mn, dict) else None
                else:
                    v.starting_price_avg = avg.get('value') if isinstance(avg, dict) else None
                    v.starting_price_min = mn.get('value') if isinstance(mn, dict) else None
        
        # If no noSeason pricing, fallback to vendorObj.startingPriceRange
        if v.starting_price_min is None and v.starting_price_avg is None:
            v.starting_price_range = vo.get('startingPriceRange', '') or v.starting_price_range
            # Parse dollars from range like "$1,000-$1,999"
            nums = re.findall(r'\$?(\d{2,6})', v.starting_price_range.replace(',', ''))
            if nums:
                vals = [int(n) for n in nums if n.isdigit()]
                if vals:
                    v.starting_price_min = float(min(vals))
                    if len(vals) > 1:
                        v.starting_price_avg = float(sum(vals) / len(vals))
                    else:
                        v.starting_price_avg = float(vals[0])
        
        # Contact (from raw)
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
        v.website_url = src.get('websiteUrl', '') or src.get('displayWebsiteUrl', '') or v.website_url
        
        # Location detail
        loc = src.get('location', {}) or {}
        v.city = loc.get('city', '') or v.city
        v.state = loc.get('state', '') or v.state
        v.service_area = loc.get('serviceArea', '') or src.get('serviceArea', '') or v.service_area
        
        # Description
        desc = src.get('description', '') or ''
        v.description_snippet = desc[:500] if desc else ''
        
        # Business details
        org = src.get('orgDetails', {}) or {}
        v.year_founded = org.get('startYear')
        v.team_size = org.get('totalMembers')
        
        # Deals
        deals_data = src.get('deals', {}) or {}
        items = deals_data.get('items', []) if isinstance(deals_data, dict) else []
        v.deal_count = len(items)
        v.deal_descriptions = [d.get('description', '')[:200] for d in items if d.get('description')]
        
        # Awards
        if not v.awards:
            v.awards = src.get('awards', []) or vo.get('awards', []) or []
        
        v.scrape_success = True
    
    async def search(self, category_slug: str, city: str, state_code: str = '') -> list:
        """Search marketplace, return list of PricingVendor (basic info only)."""
        state_part = f"-{state_code.lower()}" if state_code else ""
        url = f"https://www.theknot.com/marketplace/{category_slug}-{city.lower().replace(' ', '-')}{state_part}"
        
        print(f"  [TheKnot] Searching {category_slug}: {url}")
        await self._goto(url, wait_after=5)
        
        state = await self.page.evaluate('() => window.__INITIAL_STATE__')
        if not state:
            print("    No __INITIAL_STATE__ found")
            return []
        
        search = state.get('search', {})
        vendors = search.get('vendors', [])
        total = search.get('total', 0)
        print(f"    Found {total} results ({len(vendors)} on page)")
        
        results = []
        for v_data in vendors:
            v = self._parse_vendor(v_data, category_slug)
            v.scraped_at = datetime.utcnow().isoformat()
            results.append(v)
        
        return results
    
    async def scrape_detail(self, v: PricingVendor) -> PricingVendor:
        """Scrape detail page to enrich vendor with full pricing/contact."""
        if not v.source_url:
            return v
        try:
            await self._goto(v.source_url, wait_after=4)
            state = await self.page.evaluate('() => window.__INITIAL_STATE__')
            self._parse_detail(v, state)
        except Exception as e:
            v.scrape_success = False
        return v


# ── Zola scraper ───────────────────────────────────────────────────────────

class ZolaPricingScraper:
    """Scrape Zola for DJ, planner, and photobooth vendors."""
    
    SOURCE_SLUGS = {
        'wedding-djs': 'wedding-djs',
        'wedding-planners': 'wedding-planners',
        'wedding-photobooths': 'wedding-photobooths',
    }
    
    CAT_CODE = {
        'wedding-djs': 'DJ',
        'wedding-planners': 'COORD',
        'wedding-photobooths': 'PHOTOBOOTH',
    }
    CAT_LABEL = {
        'wedding-djs': 'DJ / MC',
        'wedding-planners': 'Wedding Coordinator',
        'wedding-photobooths': 'Photobooth',
    }
    
    def __init__(self, output_dir: str, headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser = None
    
    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            executable_path=BROWSER_PATH if os.path.exists(BROWSER_PATH) else None,
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
    
    async def _goto(self, url: str, wait_after: int = 4):
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(wait_after)
    
    def _parse_vendor(self, v_data: dict, cat_slug: str) -> PricingVendor:
        v = PricingVendor()
        v.source = 'zola'
        v.category = self.CAT_CODE.get(cat_slug, 'OTHER')
        v.category_detail = self.CAT_LABEL.get(cat_slug, cat_slug)
        v.name = v_data.get('name', '') or ''
        v.vendor_id = v_data.get('id', '') or v_data.get('slug', '')
        v.star_rating = v_data.get('averageReviewsRate', 0.0) or v_data.get('starRating', 0.0) or 0.0
        v.review_count = v_data.get('reviewCount', 0) or v_data.get('reviewsCount', 0) or 0
        
        # Pricing
        sp_cents = v_data.get('startingPriceCents', 0) or 0
        if sp_cents:
            v.starting_price_min = sp_cents / 100.0
            v.starting_price_avg = sp_cents / 100.0  # Zola shows one starting price
        sp = v_data.get('startingPrice', 0) or 0
        if sp and not v.starting_price_min:
            v.starting_price_min = float(sp)
            v.starting_price_avg = float(sp)
        
        v.price_tier = v_data.get('priceTier', '') or ''
        
        # Location
        v.city = v_data.get('city', '') or ''
        v.state = v_data.get('stateProvince', '') or ''
        
        # Contact (only on detail pages)
        v.phone = v_data.get('phone', '') or ''
        social = v_data.get('social', {}) or {}
        v.website_url = social.get('web', '') if isinstance(social, dict) else ''
        v.website_url = v.website_url or v_data.get('websiteUrl', '') or ''
        
        v.scraped_at = datetime.utcnow().isoformat()
        v.scrape_success = bool(v.name)
        
        # URL
        slug = v_data.get('slug', '') or ''
        if slug:
            v.source_url = f"https://www.zola.com/wedding-vendors/{cat_slug}/{slug}"
        
        return v
    
    async def search(self, cat_slug: str, city: str, state: str) -> list:
        url = f"https://www.zola.com/wedding-vendors/search/{city.lower().replace(' ', '-')}-{state.lower()}--{cat_slug}"
        print(f"  [Zola] Searching {cat_slug}: {url}")
        try:
            await self._goto(url, wait_after=5)
        except Exception as e:
            print(f"    Error: {e}")
            return []
        
        next_data = await self.page.evaluate('() => { const el = document.getElementById("__NEXT_DATA__"); return el ? JSON.parse(el.textContent) : null; }')
        if not next_data:
            print("    No __NEXT_DATA__ found")
            return []
        
        props = next_data.get('props', {}) or {}
        page_props = props.get('pageProps', {}) or {}
        
        vendors = []
        search_results = page_props.get('searchResults', {}) or {}
        vlist = search_results.get('vendors', [])
        total = search_results.get('totalHits', 0)
        
        # Also try alternative paths
        if not vlist:
            vsd = page_props.get('vendorSearchData', {}).get('vendorSearch', {})
            vlist = vsd.get('vendors', []) if vsd else []
        
        print(f"    Found vendors: {len(vlist)} (total: {total})")
        
        seen_ids = set()
        for v_data in vlist:
            vid = v_data.get('id', '') or v_data.get('slug', '')
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            v = self._parse_vendor(v_data, cat_slug)
            vendors.append(v)
        
        return vendors


# ── WeddingWire scraper ─────────────────────────────────────────────────────

class WeddingWirePricingScraper:
    """Scrape WeddingWire for DJ, planner, and photobooth vendors."""
    
    SLUG_MAP = {
        'wedding-djs': 'wedding-djs',
        'wedding-planners': 'wedding-planners',
        'wedding-photobooths': 'photo-booth-rentals',
    }
    CAT_CODE = {
        'wedding-djs': 'DJ',
        'wedding-planners': 'COORD',
        'wedding-photobooths': 'PHOTOBOOTH',
    }
    CAT_LABEL = {
        'wedding-djs': 'DJ / MC',
        'wedding-planners': 'Wedding Coordinator',
        'wedding-photobooths': 'Photobooth',
    }
    
    def __init__(self, output_dir: str, headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser = None
    
    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            executable_path=BROWSER_PATH if os.path.exists(BROWSER_PATH) else None,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        )
        self.page = await self.context.new_page()
    
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_pw') and self._pw:
            await self._pw.stop()
    
    async def _goto(self, url: str, wait_after: int = 4):
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(wait_after)
    
    async def search(self, cat_slug: str, location: str = '') -> list:
        ww_slug = self.SLUG_MAP.get(cat_slug, cat_slug)
        url = f"https://www.weddingwire.com/{ww_slug}"
        if location:
            url += f"?location={location}"
        
        print(f"  [WeddingWire] Searching {cat_slug}: {url}")
        try:
            await self._goto(url, wait_after=5)
        except Exception as e:
            print(f"    Error: {e}")
            return []
        
        vendors = []
        
        try:
            vendor_data = await self.page.evaluate('''() => {
                const results = [];
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
                                    });
                                }
                            });
                        }
                    } catch(e) {}
                });
                return results;
            }''')
            
            for vd in vendor_data:
                if not vd.get('name') or len(vd['name']) < 2:
                    continue
                v = PricingVendor()
                v.source = 'weddingwire'
                v.category = self.CAT_CODE.get(cat_slug, 'OTHER')
                v.category_detail = self.CAT_LABEL.get(cat_slug, cat_slug)
                v.name = vd['name']
                v.star_rating = vd.get('rating', 0.0) or 0.0
                v.review_count = vd.get('reviewCount', 0) or 0
                
                # Parse price range from string like "$500-$2,000"
                price_str = vd.get('price', '') or ''
                v.starting_price_range = price_str
                nums = re.findall(r'\$?(\d{2,6})', price_str.replace(',', ''))
                if nums:
                    vals = [int(n) for n in nums if n.isdigit()]
                    if vals:
                        v.starting_price_min = float(min(vals))
                        if len(vals) > 1:
                            v.starting_price_avg = float(sum(vals) / len(vals))
                        else:
                            v.starting_price_avg = float(vals[0])
                
                v.source_url = vd.get('url', '') or ''
                v.scraped_at = datetime.utcnow().isoformat()
                v.scrape_success = True
                vendors.append(v)
            
            print(f"    Found {len(vendors)} vendors")
        except Exception as e:
            print(f"    Error extracting: {e}")
        
        return vendors


# ── Coordinator ─────────────────────────────────────────────────────────────

async def run_scrape(args):
    """Run the full pricing scrape pipeline."""
    output_dir = args.output
    
    all_vendors: list[PricingVendor] = []
    seen_keys = set()  # Dedup by (source, vendor_id)
    
    # ── Phase 1: TheKnot ──
    print(f"\n{'='*60}")
    print("PHASE 1: THEKNOT")
    print(f"{'='*60}")
    tk = TheKnotPricingScraper(output_dir=output_dir, headless=args.headless)
    await tk.start()
    
    for cat_slug in ['wedding-djs', 'wedding-planners']:
        vendors = await tk.search(cat_slug, args.city, args.state)
        print(f"  Enriching up to {min(len(vendors), args.max_vendors)} vendors with detail pages...")
        for i, v in enumerate(vendors[:args.max_vendors]):
            v = await tk.scrape_detail(v)
            # Classify tier
            v.price_tier = classify_tier(v.category, v.starting_price_avg, v.starting_price_min)
            # Dedup
            key = ('theknot', v.vendor_id)
            if key not in seen_keys:
                seen_keys.add(key)
                all_vendors.append(v)
            if (i + 1) % 5 == 0:
                print(f"    ... {i+1}/{min(len(vendors), args.max_vendors)} done")
        print(f"  TheKnot {cat_slug}: {len([v for v in vendors if v.scrape_success])} vendors")
    
    await tk.stop()
    
    # ── Phase 2: Zola ──
    print(f"\n{'='*60}")
    print("PHASE 2: ZOLA")
    print(f"{'='*60}")
    zl = ZolaPricingScraper(output_dir=output_dir, headless=args.headless)
    await zl.start()
    
    for cat_slug in ['wedding-djs', 'wedding-planners', 'wedding-photobooths']:
        vendors = await zl.search(cat_slug, args.city, args.state)
        for v in vendors:
            v.price_tier = classify_tier(v.category, v.starting_price_avg, v.starting_price_min)
            key = ('zola', v.vendor_id)
            if key not in seen_keys:
                seen_keys.add(key)
                all_vendors.append(v)
        print(f"  Zola {cat_slug}: {len(vendors)} vendors")
    
    await zl.stop()
    
    # ── Phase 3: WeddingWire ──
    print(f"\n{'='*60}")
    print("PHASE 3: WEDDINGWIRE")
    print(f"{'='*60}")
    ww = WeddingWirePricingScraper(output_dir=output_dir, headless=args.headless)
    await ww.start()
    
    for cat_slug in ['wedding-djs', 'wedding-planners', 'wedding-photobooths']:
        vendors = await ww.search(cat_slug, location=args.city)
        for v in vendors:
            v.price_tier = classify_tier(v.category, v.starting_price_avg, v.starting_price_min)
            key = ('weddingwire', v.source_url)
            if key not in seen_keys:
                seen_keys.add(key)
                all_vendors.append(v)
        print(f"  WeddingWire {cat_slug}: {len(vendors)} vendors")
    
    await ww.stop()
    
    # ── Save output ──
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Combined JSON (latest)
    latest_path = Path(output_dir) / 'pricing_latest.json'
    with open(latest_path, 'w') as f:
        json.dump([asdict(v) for v in all_vendors], f, indent=2, default=str)
    
    # Dated archive
    archive_path = Path(output_dir) / f'pricing_{ts}.json'
    with open(archive_path, 'w') as f:
        json.dump([asdict(v) for v in all_vendors], f, indent=2, default=str)
    
    # CSV
    csv_path = Path(output_dir) / 'pricing_latest.csv'
    fields = ['source', 'category', 'category_detail', 'name', 'phone', 'email', 'website_url',
              'city', 'state', 'starting_price_min', 'starting_price_avg', 'starting_price_range',
              'price_tier', 'star_rating', 'review_count', 'ad_tier', 'vendor_tier',
              'deal_count', 'year_founded', 'team_size', 'source_url', 'scrape_success']
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for v in all_vendors:
            d = asdict(v)
            w.writerow({k: d.get(k, '') for k in fields})
    
    print(f"\n{'='*60}")
    print("SCRAPE COMPLETE")
    print(f"{'='*60}")
    print(f"  Total unique vendors: {len(all_vendors)}")
    print(f"  By source: {count_by(all_vendors, 'source')}")
    print(f"  By category: {count_by(all_vendors, 'category')}")
    print(f"  With pricing: {sum(1 for v in all_vendors if v.starting_price_min is not None)}")
    print(f"  Tiers: {count_by(all_vendors, 'price_tier')}")
    print(f"  Latest: {latest_path}")
    print(f"  Archive: {archive_path}")
    print(f"  CSV: {csv_path}")
    
    return all_vendors


def count_by(vendors: list, field: str) -> dict:
    counts = {}
    for v in vendors:
        val = getattr(v, field, 'unknown')
        counts[val] = counts.get(val, 0) + 1
    return counts


def verify_data(output_dir: str):
    """Read latest pricing data and print summary."""
    path = Path(output_dir) / 'pricing_latest.json'
    if not path.exists():
        print(f"No data at {path}")
        return
    with open(path) as f:
        data = json.load(f)
    
    print(f"\n{'='*60}")
    print(f"PRICING DATA VERIFICATION — {len(data)} vendors")
    print(f"{'='*60}")
    
    # By source
    sources = {}
    for v in data:
        s = v.get('source', '?')
        sources[s] = sources.get(s, 0) + 1
    print(f"\nSources: {sources}")
    
    # By category
    cats = {}
    for v in data:
        c = v.get('category', '?')
        cats[c] = cats.get(c, 0) + 1
    print(f"Categories: {cats}")
    
    # Pricing stats per category
    for cat in ['DJ', 'COORD', 'PHOTOBOOTH']:
        vendors = [v for v in data if v.get('category') == cat and v.get('starting_price_min')]
        if not vendors:
            print(f"\n  {cat}: No vendors with pricing")
            continue
        prices = [v['starting_price_min'] for v in vendors if v['starting_price_min']]
        avgs = [v['starting_price_avg'] for v in vendors if v['starting_price_avg']]
        print(f"\n  {cat} ({len(vendors)} with pricing):")
        print(f"    Min start: ${min(prices):.0f} | Max start: ${max(prices):.0f} | Median: ${sorted(prices)[len(prices)//2]:.0f}")
        if avgs:
            print(f"    Avg price: ${sum(avgs)/len(avgs):.0f}")
        # Tiers
        tiers = {}
        for v in vendors:
            t = v.get('price_tier', '?')
            tiers[t] = tiers.get(t, 0) + 1
        print(f"    Tiers: {tiers}")
    
    # Top vendors (with best reviews and pricing)
    print(f"\n  Top-rated by category:")
    for cat in ['DJ', 'COORD', 'PHOTOBOOTH']:
        vendors = [v for v in data if v.get('category') == cat and v.get('star_rating', 0) > 0]
        vendors.sort(key=lambda v: v.get('review_count', 0), reverse=True)
        top = vendors[:5]
        if top:
            print(f"    {cat}:")
            for v in top:
                print(f"      {v['name']} | {v['star_rating']}★({v['review_count']}) | min ${v.get('starting_price_min', '?')} | avg ${v.get('starting_price_avg', '?')} | {v.get('price_tier', '?')}")


# ── Main ────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description='Wedding Pricing Comparison Scraper')
    parser.add_argument('--city', default='indianapolis', help='City to search')
    parser.add_argument('--state', default='in', help='State code')
    parser.add_argument('--max-vendors', type=int, default=10, help='Max vendors per category to scrape detail')
    parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
    parser.add_argument('--output', default=str(Path.home() / 'wedding-pricing-data'), help='Output directory')
    parser.add_argument('--verify-only', action='store_true', help='Just verify existing data')
    parser.add_argument('--one-category', choices=['dj', 'planner', 'photobooth'], help='Scrape only one category')
    args = parser.parse_args()
    
    if args.verify_only:
        verify_data(args.output)
        return
    
    print("=" * 60)
    print("WEDDING PRICING COMPARISON SCRAPER")
    print(f"City: {args.city}, State: {args.state}, Max vendors: {args.max_vendors}")
    print("=" * 60)
    
    await run_scrape(args)


if __name__ == '__main__':
    asyncio.run(main())