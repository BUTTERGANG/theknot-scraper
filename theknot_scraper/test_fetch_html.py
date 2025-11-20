#!/usr/bin/env python3
"""
Test script to verify TheKnot scraper can bypass bot detection and fetch HTML

This script attempts to:
1. Navigate to TheKnot.com homepage or a vendor page
2. Fetch the HTML content
3. Save the HTML to a file for analysis
4. Report success/failure with detailed diagnostics
"""
import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper import TheKnotScraper
from config import ScraperConfig


def print_banner():
    """Print test banner"""
    print("=" * 70)
    print("TheKnot Scraper - HTML Fetch Test")
    print("Testing bot detection bypass capabilities")
    print("=" * 70)
    print()


def print_result(success: bool, message: str):
    """Print colored result"""
    if success:
        print(f"✅ SUCCESS: {message}")
    else:
        print(f"❌ FAILURE: {message}")


def analyze_html(html: str) -> dict:
    """Analyze fetched HTML for interesting markers"""
    analysis = {
        "length": len(html),
        "has_title": "<title>" in html.lower(),
        "has_body": "<body" in html.lower(),
        "has_403": "403" in html,
        "has_forbidden": "forbidden" in html.lower(),
        "has_access_denied": "access denied" in html.lower(),
        "has_blocked": "blocked" in html.lower(),
        "has_captcha": any(x in html.lower() for x in ["recaptcha", "hcaptcha", "px-captcha", "captcha"]),
        "has_perimeterx": "perimeterx" in html.lower() or "_px" in html,
        "has_datadome": "datadome" in html.lower(),
        "has_cloudflare": "cloudflare" in html.lower(),
        "has_content": len(html) > 10000,  # Typical page is much larger
    }
    return analysis


def test_homepage():
    """Test fetching TheKnot homepage"""
    print("\n" + "=" * 70)
    print("TEST 1: Fetch TheKnot.com Homepage")
    print("=" * 70)

    url = "https://www.theknot.com"
    print(f"Target URL: {url}")
    print()

    # Configure scraper for maximum stealth
    config = ScraperConfig(
        headless=False,  # CRITICAL: visible browser
        window_size=(1920, 1080),
        min_delay=3.0,
        max_delay=6.0,
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_screenshots=True,
        save_html=True,
        log_level="INFO",
        max_retries=2,
        retry_delay=5
    )

    print("Configuration:")
    print(f"  - Headless: {config.headless}")
    print(f"  - Delays: {config.min_delay}-{config.max_delay}s")
    print(f"  - Mouse simulation: {config.enable_mouse_movement}")
    print(f"  - Scroll simulation: {config.enable_random_scrolling}")
    print(f"  - Max retries: {config.max_retries}")
    print()

    try:
        print("Initializing scraper...")
        with TheKnotScraper(config) as scraper:
            print("✓ Scraper initialized")
            print()

            print("Attempting to fetch HTML...")
            print("(This may take 10-20 seconds with behavior simulation)")
            print()

            start_time = time.time()
            success, html, error = scraper.get_page_html(url)
            elapsed = time.time() - start_time

            print()
            print(f"Fetch completed in {elapsed:.2f} seconds")
            print()

            if success:
                print_result(True, "HTML fetched successfully!")
                print()

                # Analyze HTML
                analysis = analyze_html(html)

                print("HTML Analysis:")
                print(f"  - Length: {analysis['length']:,} characters")
                print(f"  - Has <title>: {analysis['has_title']}")
                print(f"  - Has <body>: {analysis['has_body']}")
                print(f"  - Has content (>10KB): {analysis['has_content']}")
                print()

                print("Bot Detection Indicators:")
                print(f"  - 403 error: {analysis['has_403']}")
                print(f"  - 'Forbidden' text: {analysis['has_forbidden']}")
                print(f"  - 'Access Denied': {analysis['has_access_denied']}")
                print(f"  - 'Blocked' text: {analysis['has_blocked']}")
                print(f"  - CAPTCHA detected: {analysis['has_captcha']}")
                print()

                print("Bot Detection Services:")
                print(f"  - PerimeterX: {analysis['has_perimeterx']}")
                print(f"  - DataDome: {analysis['has_datadome']}")
                print(f"  - Cloudflare: {analysis['has_cloudflare']}")
                print()

                # Save HTML to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = Path("output") / f"theknot_homepage_{timestamp}.html"
                output_file.parent.mkdir(exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)

                print(f"HTML saved to: {output_file}")
                print()

                # Extract and display title
                if "<title>" in html:
                    title_start = html.find("<title>") + 7
                    title_end = html.find("</title>")
                    title = html[title_start:title_end].strip()
                    print(f"Page Title: {title}")
                    print()

                # Show first 500 chars of body
                if "<body" in html:
                    body_start = html.find("<body")
                    body_preview = html[body_start:body_start+500]
                    print("Body Preview (first 500 chars):")
                    print("-" * 70)
                    print(body_preview)
                    print("-" * 70)
                    print()

                # Final assessment
                if analysis['has_403'] or analysis['has_forbidden'] or analysis['has_blocked']:
                    print_result(False, "Page indicates we were BLOCKED")
                    return False
                elif analysis['has_captcha']:
                    print_result(False, "CAPTCHA challenge detected")
                    print("(This may require manual solving)")
                    return False
                elif not analysis['has_content']:
                    print_result(False, "HTML too short - possible redirect or block")
                    return False
                else:
                    print_result(True, "Successfully bypassed bot detection!")
                    return True

            else:
                print_result(False, f"Failed to fetch HTML: {error}")
                return False

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return False
    except Exception as e:
        print_result(False, f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vendor_page():
    """Test fetching a sample vendor page"""
    print("\n" + "=" * 70)
    print("TEST 2: Fetch Sample Vendor Page")
    print("=" * 70)

    # This is a sample vendor URL - may or may not exist
    # Users should replace with a real vendor URL
    url = "https://www.theknot.com/marketplace/the-plaza-hotel-new-york-ny-236"
    print(f"Target URL: {url}")
    print("(Replace with actual vendor URL if this doesn't work)")
    print()

    config = ScraperConfig(
        headless=False,
        min_delay=4.0,
        max_delay=7.0,
        enable_mouse_movement=True,
        enable_random_scrolling=True,
        save_screenshots=True,
        save_html=True,
        log_level="INFO"
    )

    try:
        with TheKnotScraper(config) as scraper:
            print("Fetching vendor page HTML...")
            print()

            success, html, error = scraper.get_page_html(url)

            if success:
                analysis = analyze_html(html)

                if not (analysis['has_403'] or analysis['has_forbidden'] or analysis['has_blocked']):
                    print_result(True, "Vendor page fetched successfully!")

                    # Save HTML
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = Path("output") / f"vendor_page_{timestamp}.html"
                    output_file.parent.mkdir(exist_ok=True)

                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(html)

                    print(f"HTML saved to: {output_file}")
                    print(f"Length: {analysis['length']:,} characters")
                    return True
                else:
                    print_result(False, "Page was blocked")
                    return False
            else:
                print_result(False, f"Failed: {error}")
                return False

    except Exception as e:
        print_result(False, f"Exception: {e}")
        return False


def main():
    """Run all tests"""
    print_banner()

    print("This test will:")
    print("1. Launch a Chrome browser window (NOT headless)")
    print("2. Navigate to TheKnot.com")
    print("3. Simulate human behavior (mouse, scrolling, delays)")
    print("4. Attempt to fetch the HTML")
    print("5. Analyze the results for bot detection indicators")
    print()
    print("Note: The browser window will remain open during testing.")
    print("      This is normal and required for anti-detection.")
    print()

    input("Press ENTER to start the test...")
    print()

    # Test 1: Homepage
    test1_success = test_homepage()

    # Wait between tests
    if test1_success:
        print("\n" + "=" * 70)
        print("Test 1 passed! Waiting 10 seconds before Test 2...")
        print("=" * 70)
        time.sleep(10)

        # Test 2: Vendor page
        test2_success = test_vendor_page()
    else:
        print("\n" + "=" * 70)
        print("Test 1 failed. Skipping Test 2.")
        print("=" * 70)
        test2_success = False

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()
    print(f"Test 1 (Homepage):     {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Test 2 (Vendor Page):  {'✅ PASSED' if test2_success else '❌ FAILED (or skipped)'}")
    print()

    if test1_success:
        print("🎉 SUCCESS! The scraper can bypass TheKnot's bot detection!")
        print()
        print("Next steps:")
        print("1. Check the output/ directory for saved HTML and screenshots")
        print("2. Review the HTML to identify data extraction selectors")
        print("3. Test with real vendor URLs")
        print("4. Adjust config if needed (delays, behavior simulation)")
    else:
        print("⚠️  The test failed. Troubleshooting tips:")
        print()
        print("1. Check if you're using a datacenter IP (may be blocked)")
        print("   - Try using a residential proxy")
        print("2. Make sure headless=False (visible browser required)")
        print("3. Review logs in logs/scraper.log")
        print("4. Check screenshots in output/ directory")
        print("5. Try increasing delays (min_delay=5.0, max_delay=10.0)")
        print("6. If CAPTCHA appears, solve it manually")

    print()
    print("Check output/ directory for:")
    print("  - HTML files")
    print("  - Screenshots")
    print("  - logs/scraper.log for detailed logs")
    print()


if __name__ == "__main__":
    main()
