#!/usr/bin/env python3
"""
Single entry point to run TheKnot scraper.
Just run: python run.py
"""
import sys
import json
from pathlib import Path

# Add the scraper module to path
sys.path.insert(0, str(Path(__file__).parent / "theknot_scraper"))

from scraper import TheKnotScraper
from config import ScraperConfig


def main():
    # Default URL - change this or pass as argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default to marketplace page
        url = "https://www.theknot.com/marketplace/wedding-photographers-fishers-in"
        print("NOTE: Using default marketplace page URL.")
        print("For a single vendor, pass a vendor URL like:")
        print("  python run.py https://www.theknot.com/marketplace/vendor-name-city--12345")
        print()

    # Configure scraper
    config = ScraperConfig(
        headless=False,  # Visible browser (more reliable)
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_screenshots=True,
        save_html=True,
        min_delay=3.0,
        max_delay=6.0,
        log_level="INFO"
    )

    # Create output directory
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    print(f"Scraping: {url}")
    print("=" * 60)

    with TheKnotScraper(config) as scraper:
        # First, navigate to detect page type
        if not scraper.navigate_to_page(url):
            print("ERROR: Failed to navigate to page")
            return

        page_type = scraper.detect_page_type()
        print(f"\nDetected page type: {page_type.upper()}")
        print("-" * 60)

        if page_type == "marketplace":
            # Extract vendor URLs from marketplace page
            print("\nExtracting vendor URLs from marketplace page...")
            vendor_urls = scraper.scrape_marketplace_page(url, max_vendors=5)  # Limit to 5 for demo

            if not vendor_urls:
                print("ERROR: No vendor URLs found on marketplace page")
                print("Check the saved screenshots/HTML in the output directory")
                return

            print(f"\nFound {len(vendor_urls)} vendor URLs:")
            for i, vendor_url in enumerate(vendor_urls, 1):
                print(f"  {i}. {vendor_url}")

            # Scrape first vendor as example
            print(f"\nScraping first vendor as example...")
            vendor_data = scraper.scrape_vendor_page(vendor_urls[0])

            # Display results
            print("\n" + "=" * 60)
            print("VENDOR DATA:")
            print("=" * 60)
            print(f"Business Name: {vendor_data.business_name}")
            print(f"Starting Price: {vendor_data.starting_price}")
            print(f"Packages Found: {len(vendor_data.packages)}")
            print(f"Success: {vendor_data.success}")

            if vendor_data.error_message:
                print(f"Error: {vendor_data.error_message}")

            # Save to JSON
            output_file = output_dir / "vendor_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(vendor_data.to_dict(), f, indent=2, ensure_ascii=False)

            # Save vendor URLs list
            urls_file = output_dir / "vendor_urls.json"
            with open(urls_file, 'w', encoding='utf-8') as f:
                json.dump({"marketplace_url": url, "vendor_urls": vendor_urls}, f, indent=2)

            print(f"\nVendor data saved to: {output_file}")
            print(f"Vendor URLs saved to: {urls_file}")
            print(f"\nTo scrape all vendors, use: python theknot_scraper/example_multiple_vendors.py")

        elif page_type == "vendor":
            # Direct vendor page scraping
            print("\nScraping vendor page...")
            vendor_data = scraper.scrape_vendor_page(url)

            # Display results
            print("\n" + "=" * 60)
            print("VENDOR DATA:")
            print("=" * 60)
            print(f"Business Name: {vendor_data.business_name}")
            print(f"Starting Price: {vendor_data.starting_price}")
            print(f"Packages Found: {len(vendor_data.packages)}")
            print(f"Success: {vendor_data.success}")

            if vendor_data.error_message:
                print(f"Error: {vendor_data.error_message}")

            # Save to JSON
            output_file = output_dir / "vendor_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(vendor_data.to_dict(), f, indent=2, ensure_ascii=False)

            print(f"\nData saved to: {output_file}")

        else:
            print(f"\nERROR: Unable to determine page type for URL: {url}")
            print("This might be an unsupported page or bot detection is active.")
            print("Check the saved screenshots/HTML in the output directory")


if __name__ == "__main__":
    main()
