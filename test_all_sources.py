"""
END TO END TEST — run all scrapers, save comprehensive dataset
"""
import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

async def main():
    # Import scrapers
    sys.path.insert(0, str(Path.cwd()))
    
    print("=" * 60)
    print("COMPREHENSIVE WEDDING VENDOR SCRAPER TEST")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    summary = {}
    
    # === THEKNOT ===
    print("\n" + "=" * 60)
    print("1. THEKNOT SCRAPER")
    print("=" * 60)
    
    from theknot_scraper_v2 import TheKnotScraperV2
    
    tk = TheKnotScraperV2(output_dir=str(OUT))
    try:
        await tk.start()
        vendors = await tk.scrape_marketplace_and_details(
            city='indianapolis', category='wedding-photographers', state_code='in', max_vendors=5
        )
        summary['theknot'] = {
            'vendors_found': len(vendors),
            'successful': sum(1 for v in vendors if v.scrape_success),
            'with_phone': sum(1 for v in vendors if v.phone),
            'with_email': sum(1 for v in vendors if v.email),
            'with_rating': sum(1 for v in vendors if v.star_rating),
            'with_pricing': sum(1 for v in vendors if v.starting_price_min),
        }
    finally:
        await tk.stop()
    
    # === ZOLA ===
    print("\n" + "=" * 60)
    print("2. ZOLA SCRAPER")
    print("=" * 60)
    
    from zola_scraper import ZolaScraper
    
    zola = ZolaScraper(output_dir=str(OUT))
    try:
        await zola.start()
        vendors = await zola.search_vendors(city='new-york', state='ny', category='wedding-photographers')
        summary['zola'] = {
            'vendors_found': len(vendors),
            'successful': sum(1 for v in vendors if v.scrape_success),
            'with_rating': sum(1 for v in vendors if v.star_rating),
            'with_pricing': sum(1 for v in vendors if v.starting_price),
        }
    finally:
        await zola.stop()
    
    # === WEDDINGWIRE ===
    print("\n" + "=" * 60)
    print("3. WEDDINGWIRE SCRAPER")
    print("=" * 60)
    
    from weddingwire_scraper import WeddingWireScraper
    
    ww = WeddingWireScraper(output_dir=str(OUT))
    try:
        await ww.start()
        vendors = await ww.search_vendors(category='wedding-photographers')
        summary['weddingwire'] = {
            'vendors_found': len(vendors),
            'successful': sum(1 for v in vendors if v.scrape_success),
            'with_rating': sum(1 for v in vendors if v.rating),
            'with_pricing': sum(1 for v in vendors if v.starting_price),
        }
    finally:
        await ww.stop()
    
    # === SUMMARY ===
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_vendors = 0
    for source, stats in summary.items():
        print(f"\n{source.upper()}:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        total_vendors += stats['vendors_found']
    
    print(f"\nTotal vendors across all sources: {total_vendors}")
    
    # Save summary
    summary_path = OUT / 'scraping_summary.json'
    with open(summary_path, 'w') as f:
        json.dump({
            'test_date': datetime.utcnow().isoformat(),
            'summary': summary,
            'total_vendors': total_vendors,
        }, f, indent=2)
    print(f"\nSummary saved to {summary_path}")
    print(f"\nAll output files in: {OUT}")
    
    # List all output files
    print("\nOutput files:")
    for f in sorted(OUT.glob('*')):
        print(f"  {f.name}: {f.stat().st_size:,} bytes")

if __name__ == '__main__':
    asyncio.run(main())