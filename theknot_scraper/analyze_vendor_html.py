#!/usr/bin/env python3
"""
Fetch and analyze HTML structure from TheKnot vendor page

This script uses the scraper to fetch a real vendor page and analyze
the actual HTML structure to update selectors.

Usage:
    python analyze_vendor_html.py
"""
import sys
from pathlib import Path
import json
import re

# Add scraper to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper import TheKnotScraper
from config import ScraperConfig


def analyze_html_structure(html: str, url: str):
    """Analyze HTML and suggest selectors"""

    print("=" * 80)
    print("HTML STRUCTURE ANALYSIS")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"HTML Length: {len(html):,} characters")
    print()

    # Find vendor name patterns
    print("1. VENDOR NAME ANALYSIS")
    print("-" * 80)

    # Look for h1 tags (most likely vendor name)
    h1_pattern = r'<h1[^>]*class="([^"]*)"[^>]*>([^<]+)</h1>'
    h1_matches = re.findall(h1_pattern, html, re.IGNORECASE)

    if h1_matches:
        print("Found H1 tags:")
        for classes, text in h1_matches[:3]:
            print(f"  Class: {classes}")
            print(f"  Text: {text.strip()}")
            print()

    # Alternative: Look for data-testid attributes
    vendor_testid = re.findall(r'data-testid="([^"]*vendor[^"]*)"', html, re.IGNORECASE)
    if vendor_testid:
        print(f"Found vendor test IDs: {vendor_testid[:5]}")
        print()

    # Find pricing patterns
    print("\n2. PRICING ANALYSIS")
    print("-" * 80)

    # Look for price mentions
    price_pattern = r'<[^>]*class="([^"]*)"[^>]*>\$[\d,]+</[^>]*>'
    price_matches = re.findall(price_pattern, html)

    if price_matches:
        print("Found elements with prices:")
        for classes in set(price_matches[:10]):
            print(f"  Class: {classes}")

    # Look for "starting" price text
    starting_pattern = r'<[^>]*>([^<]*starting[^<]*\$[\d,]+[^<]*)</[^>]*>'
    starting_matches = re.findall(starting_pattern, html, re.IGNORECASE)

    if starting_matches:
        print("\nFound 'starting' price text:")
        for text in starting_matches[:3]:
            print(f"  {text.strip()}")

    print()

    # Find package/pricing section
    print("\n3. PACKAGES SECTION ANALYSIS")
    print("-" * 80)

    # Look for package-related classes
    package_keywords = ['package', 'pricing', 'tier', 'plan', 'offer']

    for keyword in package_keywords:
        pattern = f'class="([^"]*{keyword}[^"]*)"'
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            unique_classes = set(matches)
            print(f"\nClasses containing '{keyword}':")
            for cls in list(unique_classes)[:5]:
                print(f"  {cls}")

    # Look for common container patterns
    print("\n\n4. COMMON CONTAINERS")
    print("-" * 80)

    # Find main content containers
    containers = re.findall(r'<(div|section|article)[^>]*class="([^"]*)"[^>]*>', html)

    # Count class frequency
    class_freq = {}
    for tag, classes in containers:
        for cls in classes.split():
            if cls and len(cls) > 3:  # Skip very short classes
                class_freq[cls] = class_freq.get(cls, 0) + 1

    # Show most common classes
    sorted_classes = sorted(class_freq.items(), key=lambda x: x[1], reverse=True)
    print("Most common classes (likely main containers):")
    for cls, count in sorted_classes[:10]:
        print(f"  {cls}: {count} occurrences")

    print()

    # Extract sample HTML sections
    print("\n5. SAMPLE HTML SECTIONS")
    print("-" * 80)

    # Find first h1 with context
    h1_start = html.find('<h1')
    if h1_start > 0:
        h1_section = html[max(0, h1_start-200):h1_start+500]
        print("\nVendor Name Section (H1 context):")
        print(h1_section)
        print()

    # Find first price mention with context
    price_start = html.find('$')
    if price_start > 0:
        price_section = html[max(0, price_start-200):price_start+300]
        print("\nPrice Section Context:")
        print(price_section)
        print()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()

    return {
        'h1_classes': [classes for classes, _ in h1_matches],
        'price_classes': list(set(price_matches[:10])),
        'vendor_testids': vendor_testid[:5],
    }


def suggest_selectors(analysis: dict):
    """Suggest updated selectors based on analysis"""

    print("SUGGESTED SELECTOR UPDATES")
    print("=" * 80)
    print()

    print("# config.py updates")
    print("-" * 80)
    print()
    print("SELECTORS = {")

    # Vendor name selectors
    print("    'vendor_name': [")
    if analysis['h1_classes']:
        for cls in analysis['h1_classes']:
            if cls:
                print(f"        'h1.{cls.split()[0]}',")
    if analysis['vendor_testids']:
        for testid in analysis['vendor_testids']:
            print(f"        '[data-testid=\"{testid}\"]',")
    print("        'h1',  # Fallback")
    print("    ],")

    # Price selectors
    print("    'starting_price': [")
    if analysis['price_classes']:
        for cls in analysis['price_classes'][:5]:
            if cls:
                print(f"        '.{cls.split()[0]}',")
    print("        '[data-testid*=\"price\"]',")
    print("        '.starting-price',")
    print("    ],")

    print("}")
    print()


def main():
    """Main analysis function"""

    # Vendor page to analyze
    vendor_url = "https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212"

    print("=" * 80)
    print("TheKnot Vendor Page HTML Analyzer")
    print("=" * 80)
    print()
    print(f"Target URL: {vendor_url}")
    print()
    print("This script will:")
    print("  1. Fetch the HTML using the scraper")
    print("  2. Analyze the structure")
    print("  3. Suggest selector updates")
    print()
    input("Press ENTER to continue...")
    print()

    # Configure scraper
    config = ScraperConfig(
        headless=False,  # Visible browser recommended
        min_delay=3.0,
        max_delay=6.0,
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_html=True,
        save_screenshots=True,
        log_level="INFO"
    )

    print("Initializing scraper...")
    print()

    try:
        with TheKnotScraper(config) as scraper:
            print("Fetching HTML (this may take 15-30 seconds)...")
            success, html, error = scraper.get_page_html(vendor_url)

            if not success:
                print(f"\n❌ Failed to fetch HTML: {error}")
                print("\nTroubleshooting:")
                print("  - Check if you're using a residential IP")
                print("  - Ensure Chrome/Chromium is installed")
                print("  - Try increasing delays in config")
                return 1

            print(f"\n✅ Successfully fetched HTML ({len(html):,} characters)")
            print()

            # Save HTML for manual inspection
            html_file = Path("output/vendor_page_analysis.html")
            html_file.parent.mkdir(exist_ok=True)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"HTML saved to: {html_file}")
            print()

            # Analyze structure
            print("Analyzing HTML structure...")
            print()

            analysis = analyze_html_structure(html, vendor_url)

            # Suggest selectors
            suggest_selectors(analysis)

            # Save analysis
            analysis_file = Path("output/selector_analysis.json")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            print(f"\nAnalysis saved to: {analysis_file}")
            print()

            print("=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print()
            print("1. Review the HTML in: output/vendor_page_analysis.html")
            print("2. Use browser DevTools to inspect elements:")
            print("   - Open the HTML file in Chrome")
            print("   - Right-click elements and 'Inspect'")
            print("   - Copy actual class names and structure")
            print()
            print("3. Update config.py SELECTORS with actual class names")
            print()
            print("4. Test with: python example_single_vendor.py")
            print()

            return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
