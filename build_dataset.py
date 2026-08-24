"""
FULL DATASET SCRAPE — all sources, multiple categories, writes to PostgreSQL
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import db_writer

OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/bulk')
OUT.mkdir(exist_ok=True, parents=True)

# Categories to scrape
CATEGORIES = {
    'wedding-photographers': 'WPH',
    'wedding-venues': 'REC',
    'wedding-planners': 'WPL',
    'wedding-florists': 'WFL',
    'wedding-caterers': 'WCA',
    'wedding-djs': 'WDJ',
}

LOCATIONS = {
    'theknot': [('indianapolis', 'in'), ('chicago', 'il'), ('new-york', 'ny')],
    'zola': [('new-york', 'ny'), ('chicago', 'il')],
}


async def scrape_theknot_bulk():
    """TheKnot: 6 categories x 3 cities, 5 vendors each = 90 detail pages"""
    from theknot_scraper_v2 import TheKnotScraperV2
    
    total_vendors = 0
    total_success = 0
    
    for city, state in LOCATIONS['theknot']:
        for cat_slug, cat_code in CATEGORIES.items():
            cat_name = cat_slug.replace('wedding-', '').replace('-', ' ')
            print(f"\n--- TheKnot: {cat_name} in {city}, {state} ---")
            
            run_id = db_writer.start_run('theknot', cat_slug, city, state)
            tk = TheKnotScraperV2(output_dir=str(OUT))
            await tk.start()
            
            try:
                # Get search results (30 vendors)
                search_vendors = await tk.search_marketplace(city, cat_slug, state)
                print(f"  Search found {len(search_vendors)} vendors")
                
                if not search_vendors:
                    db_writer.finish_run(run_id, 0, 0, 'No search results')
                    await tk.stop()
                    continue
                
                # Take first 5 for detail scraping
                urls_to_scrape = [(v.theknot_url, v.name) for v in search_vendors[:5] if v.theknot_url]
                
                for i, (url, v_name) in enumerate(urls_to_scrape, 1):
                    try:
                        await tk.page.goto(url, wait_until='domcontentloaded', timeout=20000)
                        await asyncio.sleep(3 + (i % 2))  # 3-4s delay
                        
                        state_data = await tk.page.evaluate('() => window.__INITIAL_STATE__')
                        
                        vendor_data = None
                        if state_data:
                            raw = (state_data.get('vendor') or {}).get('vendorRaw') or {}
                            v_obj = (state_data.get('vendor') or {}).get('vendor') or {}
                            
                            if raw.get('name'):
                                vendor_data = {
                                    'source': 'theknot',
                                    'vendor_id': raw.get('vendorId', ''),
                                    'marketplace_id': raw.get('id', ''),
                                    'name': raw.get('name', ''),
                                    'phone': raw.get('phones', [{}])[0].get('number', '') if raw.get('phones') else '',
                                    'email': raw.get('emails', [{}])[0].get('address', '') if raw.get('emails') else '',
                                    'website_url': raw.get('websiteUrl', '') or '',
                                    'display_website_url': raw.get('displayWebsiteUrl', '') or '',
                                    'address_city': (raw.get('location') or {}).get('city', '') or '',
                                    'address_state': (raw.get('location') or {}).get('state', '') or '',
                                    'service_area': (raw.get('location') or {}).get('serviceArea', '') or '',
                                    'starting_price_min': (raw.get('pricing') or {}).get('noSeason', {}).get('min', {}).get('value'),
                                    'starting_price_avg': (raw.get('pricing') or {}).get('noSeason', {}).get('average', {}).get('value'),
                                    'starting_price_range': v_obj.get('startingPriceRange', '') or '',
                                    'star_rating': (raw.get('reviewSummary') or {}).get('overallRating', 0) or v_obj.get('starCount', 0) or 0,
                                    'review_count': (raw.get('reviewSummary') or {}).get('count', 0) or raw.get('reviewsCount', 0) or 0,
                                    'description': (raw.get('description') or '')[:5000],
                                    'headline': raw.get('headline', '') or '',
                                    'ad_tier': raw.get('adTier', '') or '',
                                    'vendor_tier': raw.get('vendorTier', '') or '',
                                    'year_founded': (raw.get('orgDetails') or {}).get('startYear'),
                                    'team_size': (raw.get('orgDetails') or {}).get('totalMembers'),
                                    'travel_distance': (raw.get('orgDetails') or {}).get('travelAvailability'),
                                    'facebook_url': (raw.get('social') or {}).get('facebookUrl', '') or '',
                                    'instagram_username': (raw.get('social') or {}).get('instagramUsername', '') or '',
                                    'pinterest_username': (raw.get('social') or {}).get('pinterestUsername', '') or '',
                                    'awards': raw.get('awards', []) or v_obj.get('awards', []) or [],
                                    'deals': (raw.get('deals') or {}).get('items', []) or [],
                                    'theknot_url': url,
                                    'category': cat_slug,
                                    'scrape_success': True,
                                }
                        
                        if vendor_data:
                            ok = db_writer.upsert_vendor(vendor_data, run_id)
                            if ok:
                                total_success += 1
                                nm = vendor_data.get('name', '')
                                ph = vendor_data.get('phone', '')
                                em = vendor_data.get('email', '')
                                print(f"  [{i:2d}] ✅ {nm[:40]:40s} | {ph or '—'} | {em or '—'}")
                            else:
                                print(f"  [{i:2d}] ❌ DB write failed")
                        else:
                            print(f"  [{i:2d}] ⚠️ No state data for {v_name[:40]}")
                        
                        total_vendors += 1
                        
                    except Exception as e:
                        print(f"  [{i:2d}] ❌ Error: {str(e)[:60]}")
                        total_vendors += 1
                
                db_writer.finish_run(run_id, len(urls_to_scrape), total_success, '')
                
            finally:
                await tk.stop()
    
    return total_vendors, total_success


async def scrape_zola_bulk():
    """Zola: 6 categories x 2 cities, 10 vendors each = 120 search results"""
    from zola_scraper import ZolaScraper
    
    total_vendors = 0
    total_success = 0
    
    for city, state in LOCATIONS['zola']:
        for cat_slug, cat_code in CATEGORIES.items():
            cat_name = cat_slug.replace('wedding-', '').replace('-', ' ')
            print(f"\n--- Zola: {cat_name} in {city}, {state} ---")
            
            run_id = db_writer.start_run('zola', cat_slug, city, state)
            zola = ZolaScraper(output_dir=str(OUT))
            await zola.start()
            
            try:
                await zola._goto(
                    f"https://www.zola.com/wedding-vendors/search/{city}-{state}--{cat_slug}",
                    5
                )
                
                nd = await zola._extract_next_data()
                if not nd:
                    print("  No __NEXT_DATA__ found")
                    db_writer.finish_run(run_id, 0, 0, 'No __NEXT_DATA__')
                    await zola.stop()
                    continue
                
                sr = nd.get('props', {}).get('pageProps', {}).get('searchResults', {})
                vendors_list = sr.get('vendors', [])
                total_hits = sr.get('totalHits', 0)
                
                print(f"  Total results: {total_hits}, returning: {len(vendors_list)}")
                
                for v in vendors_list[:10]:
                    vendor_data = {
                        'source': 'zola',
                        'vendor_id': v.get('storefrontUuid', '') or v.get('slug', ''),
                        'name': v.get('name', ''),
                        'slug': v.get('slug', ''),
                        'city': v.get('city', '') or '',
                        'state': v.get('stateProvince', '') or '',
                        'price_tier': v.get('priceTier', '') or '',
                        'starting_price': f"${v.get('startingPriceCents', 0)/100:.0f}" if v.get('startingPriceCents') else '',
                        'star_rating': v.get('averageReviewsRate', 0) or 0,
                        'review_count': v.get('reviewsCount', 0) or 0,
                        'description': (v.get('aboutVendor', '') or v.get('description', '') or '')[:2000],
                        'category': cat_slug,
                        'source_url': f"https://www.zola.com/wedding-vendors/{cat_slug}/{v.get('slug', '')}" if v.get('slug') else '',
                        'scrape_success': True,
                    }
                    
                    ok = db_writer.upsert_vendor(vendor_data, run_id)
                    if ok:
                        total_success += 1
                        print(f"  ✅ {vendor_data['name'][:40]:40s} | {vendor_data.get('starting_price', '—'):>8s} | {vendor_data['star_rating']}★")
                    total_vendors += 1
                
                db_writer.finish_run(run_id, len(vendors_list[:10]), total_success, f'Found {total_hits} total')
                
            finally:
                await zola.stop()
    
    return total_vendors, total_success


async def scrape_weddingwire_bulk():
    """WeddingWire: 6 categories, search page data"""
    import weddingwire_scraper
    from weddingwire_scraper import WeddingWireScraper
    
    total_vendors = 0
    total_success = 0
    
    for cat_slug, cat_code in CATEGORIES.items():
        cat_name = cat_slug.replace('wedding-', '').replace('-', ' ')
        print(f"\n--- WeddingWire: {cat_name} ---")
        
        run_id = db_writer.start_run('weddingwire', cat_slug)
        ww = WeddingWireScraper(output_dir=str(OUT))
        await ww.start()
        
        try:
            await ww._goto(f"https://www.weddingwire.com/{cat_slug}", 5)
            
            # Parse JSON-LD from page
            vendor_data = await ww.page.evaluate('''() => {
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
            
            print(f"  Found {len(vendor_data)} vendors from JSON-LD")
            
            for v in vendor_data[:10]:
                vendor_dict = {
                    'source': 'weddingwire',
                    'vendor_id': v.get('name', '').replace(' ', '-').lower(),
                    'name': v.get('name', ''),
                    'star_rating': v.get('rating', 0),
                    'review_count': v.get('reviewCount', 0),
                    'starting_price': v.get('price', ''),
                    'description': (v.get('description', '') or '')[:2000],
                    'biz_url': v.get('url', ''),
                    'category': cat_slug,
                    'scrape_success': True,
                }
                
                ok = db_writer.upsert_vendor(vendor_dict, run_id)
                if ok:
                    total_success += 1
                    print(f"  ✅ {vendor_dict['name'][:45]:45s} | {vendor_dict['star_rating']}★ ({vendor_dict['review_count']})")
                total_vendors += 1
            
            db_writer.finish_run(run_id, len(vendor_data[:10]), total_success, '')
            
        finally:
            await ww.stop()
    
    return total_vendors, total_success


async def main():
    print("=" * 70)
    print("FULL WEDDING VENDOR DATASET BUILD")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 70)
    
    print(f"\nTarget: 6 categories x 3-2 locations x 5-10 vendors each = ~150+ records")
    
    grand_total = 0
    grand_success = 0
    
    # TheKnot (rich detail data)
    tk_v, tk_s = await scrape_theknot_bulk()
    grand_total += tk_v
    grand_success += tk_s
    
    # Zola (search data)
    z_v, z_s = await scrape_zola_bulk()
    grand_total += z_v
    grand_success += z_s
    
    # WeddingWire (category listing data)
    ww_v, ww_s = await scrape_weddingwire_bulk()
    grand_total += ww_v
    grand_success += ww_s
    
    # Summary
    print("\n" + "=" * 70)
    print("DATASET BUILD COMPLETE")
    print("=" * 70)
    print(f"\n  Total vendors processed: {grand_total}")
    print(f"  Successfully written to DB: {grand_success}")
    
    # DB stats
    stats = db_writer.get_stats()
    print(f"\n  DB total vendors: {stats['total']}")
    for source, count in stats['by_source'].items():
        phone = stats['with_phone'].get(source, 0)
        email = stats['with_email'].get(source, 0)
        price = stats['with_pricing'].get(source, 0)
        print(f"    {source}: {count} | phone: {phone} | email: {email} | pricing: {price}")
    
    print(f"\n  All data in PostgreSQL 'wedding_vendors' on port 54329")

if __name__ == '__main__':
    asyncio.run(main())