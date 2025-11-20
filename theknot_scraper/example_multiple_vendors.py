"""
Example: Scrape multiple vendor pages from TheKnot.com
"""
import json
import csv
from pathlib import Path
from datetime import datetime

from scraper import TheKnotScraper
from config import ScraperConfig


def main():
    """Scrape multiple vendor pages"""

    # List of vendor URLs to scrape (replace with actual URLs)
    vendor_urls = [
        "https://www.theknot.com/marketplace/vendor1-city-state-123456",
        "https://www.theknot.com/marketplace/vendor2-city-state-123457",
        "https://www.theknot.com/marketplace/vendor3-city-state-123458",
        # Add more URLs here
    ]

    # Configure scraper
    config = ScraperConfig(
        headless=False,
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_screenshots=True,
        save_html=False,  # Disable HTML saving for multiple vendors
        min_delay=5.0,  # Longer delays for multiple requests
        max_delay=10.0,
        log_level="INFO"
    )

    # Create output directory
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    # Scrape all vendors
    print(f"Scraping {len(vendor_urls)} vendors")
    print("=" * 60)

    with TheKnotScraper(config) as scraper:
        results = scraper.scrape_multiple_vendors(vendor_urls)

        # Display summary
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)

        successful = [v for v in results if v.success]
        failed = [v for v in results if not v.success]

        print(f"\nTotal: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")

        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        for idx, vendor in enumerate(results, 1):
            print(f"\n{idx}. {vendor.business_name or 'UNKNOWN'}")
            print(f"   URL: {vendor.url}")
            print(f"   Starting Price: {vendor.starting_price}")
            print(f"   Packages: {len(vendor.packages)}")
            print(f"   Success: {vendor.success}")
            if vendor.error_message:
                print(f"   Error: {vendor.error_message}")

        # Save to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = output_dir / f"vendors_{timestamp}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([v.to_dict() for v in results], f, indent=2, ensure_ascii=False)

        print(f"\nJSON data saved to: {json_file}")

        # Save to CSV
        csv_file = output_dir / f"vendors_{timestamp}.csv"

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'business_name', 'url', 'starting_price', 'starting_price_numeric',
                'num_packages', 'success', 'error_message', 'scrape_timestamp'
            ])
            writer.writeheader()

            for vendor in results:
                writer.writerow({
                    'business_name': vendor.business_name,
                    'url': vendor.url,
                    'starting_price': vendor.starting_price,
                    'starting_price_numeric': vendor.starting_price_numeric,
                    'num_packages': len(vendor.packages),
                    'success': vendor.success,
                    'error_message': vendor.error_message,
                    'scrape_timestamp': vendor.scrape_timestamp
                })

        print(f"CSV data saved to: {csv_file}")

        # Save detailed packages to separate CSV
        packages_csv_file = output_dir / f"packages_{timestamp}.csv"

        with open(packages_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'business_name', 'vendor_url', 'package_number',
                'package_name', 'package_price', 'package_description'
            ])
            writer.writeheader()

            for vendor in results:
                for package in vendor.packages:
                    writer.writerow({
                        'business_name': vendor.business_name,
                        'vendor_url': vendor.url,
                        'package_number': package['package_number'],
                        'package_name': package['name'],
                        'package_price': package['price'],
                        'package_description': package['description']
                    })

        print(f"Packages CSV saved to: {packages_csv_file}")


if __name__ == "__main__":
    main()
