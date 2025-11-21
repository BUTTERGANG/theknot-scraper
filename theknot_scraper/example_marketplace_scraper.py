#!/usr/bin/env python3
"""
Example: Scrape marketplace page to find vendor URLs, then scrape each vendor

This demonstrates the two-step process:
1. Scrape marketplace/search page to extract vendor URLs
2. Scrape each vendor page for detailed information
"""
import sys
import json
import time
from pathlib import Path

# Add parent directory to path if running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))

from scraper import TheKnotScraper
from config import ScraperConfig


def main():
    # Marketplace URL (search results page)
    marketplace_url = "https://www.theknot.com/marketplace/wedding-photographers-fishers-in"

    # Configure scraper
    config = ScraperConfig(
        headless=False,
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_screenshots=True,
        save_html=True,
        min_delay=3.0,
        max_delay=6.0,
        log_level="INFO"
    )

    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("THEKNOT MARKETPLACE SCRAPER")
    print("=" * 80)
    print(f"\nStep 1: Extracting vendor URLs from marketplace page")
    print(f"URL: {marketplace_url}\n")

    with TheKnotScraper(config) as scraper:
        # Step 1: Extract vendor URLs from marketplace page
        vendor_urls = scraper.scrape_marketplace_page(marketplace_url)

        if not vendor_urls:
            print("\nERROR: No vendor URLs found!")
            print("Possible reasons:")
            print("  1. Page structure has changed (selectors need updating)")
            print("  2. Bot detection is active")
            print("  3. Network issues")
            print("\nCheck output/marketplace_*.png and output/marketplace_*.html for debugging")
            return

        print(f"\n{'='*80}")
        print(f"Found {len(vendor_urls)} vendors")
        print(f"{'='*80}\n")

        # Display all vendor URLs
        for i, url in enumerate(vendor_urls, 1):
            print(f"{i:2d}. {url}")

        # Save vendor URLs
        urls_file = output_dir / "marketplace_vendor_urls.json"
        with open(urls_file, 'w', encoding='utf-8') as f:
            json.dump({
                "marketplace_url": marketplace_url,
                "total_vendors": len(vendor_urls),
                "vendor_urls": vendor_urls,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, indent=2)
        print(f"\nVendor URLs saved to: {urls_file}")

        # Step 2: Scrape each vendor (or subset)
        print(f"\n{'='*80}")
        print(f"Step 2: Scraping individual vendor pages")
        print(f"{'='*80}\n")

        # Limit to first 3 for demonstration
        max_to_scrape = min(3, len(vendor_urls))
        print(f"Scraping first {max_to_scrape} vendors (change max_to_scrape to scrape more)\n")

        all_vendor_data = []

        for idx, vendor_url in enumerate(vendor_urls[:max_to_scrape], 1):
            print(f"\n{'-'*80}")
            print(f"Scraping vendor {idx}/{max_to_scrape}")
            print(f"{'-'*80}")

            vendor_data = scraper.scrape_vendor_page(vendor_url)

            # Display results
            status = "✓ SUCCESS" if vendor_data.success else "✗ FAILED"
            print(f"\nStatus: {status}")
            print(f"Business Name: {vendor_data.business_name or 'NOT FOUND'}")
            print(f"Starting Price: {vendor_data.starting_price or 'NOT FOUND'}")
            print(f"Packages: {len(vendor_data.packages)}")

            if vendor_data.error_message:
                print(f"Error: {vendor_data.error_message}")

            all_vendor_data.append(vendor_data.to_dict())

            # Delay between vendors to avoid detection
            if idx < max_to_scrape:
                delay = config.min_delay + 2
                print(f"\nWaiting {delay:.1f}s before next vendor...")
                time.sleep(delay)

        # Save all results
        results_file = output_dir / "all_vendors_data.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "marketplace_url": marketplace_url,
                "total_vendors_found": len(vendor_urls),
                "vendors_scraped": len(all_vendor_data),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "vendors": all_vendor_data
            }, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print("SCRAPING COMPLETE")
        print(f"{'='*80}")
        print(f"\nResults saved to: {results_file}")

        # Summary
        successful = sum(1 for v in all_vendor_data if v.get('success'))
        print(f"\nSummary:")
        print(f"  Total vendors found: {len(vendor_urls)}")
        print(f"  Vendors scraped: {len(all_vendor_data)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {len(all_vendor_data) - successful}")


if __name__ == "__main__":
    main()
