"""
Example: Scrape a single vendor page from TheKnot.com
"""
import json
from pathlib import Path

from scraper import TheKnotScraper
from config import ScraperConfig


def main():
    """Scrape a single vendor page"""

    # Real vendor URL for testing
    vendor_url = "https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212"

    # Configure scraper
    config = ScraperConfig(
        headless=False,  # Run with visible browser (recommended for first run)
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

    # Scrape vendor page
    print(f"Scraping vendor: {vendor_url}")
    print("=" * 60)

    with TheKnotScraper(config) as scraper:
        vendor_data = scraper.scrape_vendor_page(vendor_url)

        # Display results
        print(f"\nBusiness Name: {vendor_data.business_name}")
        print(f"Starting Price: {vendor_data.starting_price}")

        if vendor_data.starting_price_numeric:
            print(f"Starting Price (numeric): ${vendor_data.starting_price_numeric:,.2f}")

        print(f"\nPackages Found: {len(vendor_data.packages)}")

        for package in vendor_data.packages:
            print(f"\n  Package #{package['package_number']}:")
            print(f"    Name: {package['name']}")
            print(f"    Price: {package['price']}")
            print(f"    Description: {package['description'][:100]}...")

        print(f"\nSuccess: {vendor_data.success}")
        if vendor_data.error_message:
            print(f"Error: {vendor_data.error_message}")

        # Save to JSON
        output_file = output_dir / "vendor_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(vendor_data.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"\nData saved to: {output_file}")


if __name__ == "__main__":
    main()
