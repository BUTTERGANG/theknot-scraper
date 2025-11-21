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
    # Default vendor URL - change this or pass as argument
    if len(sys.argv) > 1:
        vendor_url = sys.argv[1]
    else:
        vendor_url = "https://www.theknot.com/marketplace/wedding-photographers-fishers-in"

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

    print(f"Scraping: {vendor_url}")
    print("=" * 60)

    with TheKnotScraper(config) as scraper:
        vendor_data = scraper.scrape_vendor_page(vendor_url)

        # Display results
        print(f"\nBusiness Name: {vendor_data.business_name}")
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


if __name__ == "__main__":
    main()
