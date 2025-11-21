# Bot Detection Analysis - TheKnot Scraper

## Issue Summary

Based on the provided logs, the scraper is failing to extract vendor information, specifically:
- ❌ Business name not found
- ❌ Packages section not found
- ✅ Starting price found: "Starting at $1,695"
- ❌ Overall scraping marked as incomplete

## Root Cause Analysis

### Primary Issue: Wrong Page Type

**The fundamental problem is NOT bot detection - it's a page type mismatch.**

The URL being scraped is:
```
https://www.theknot.com/marketplace/wedding-photographers-fishers-in
```

This is a **MARKETPLACE LISTING PAGE** (search results showing multiple photographers), NOT an individual vendor page.

### Evidence from Logs

```
2025-11-21 02:42:37 | INFO     | Loaded 32 cookies from cookies/theknot_cookies.pkl
2025-11-21 02:42:54 | INFO     | Saved 40 cookies to cookies/theknot_cookies.pkl
2025-11-21 02:42:54 | INFO     | Navigation successful
```

Key observations:
1. ✅ Navigation was **successful** - no blocks or CAPTCHAs
2. ✅ Cookies were loaded and saved properly
3. ✅ The scraper waited over 4 minutes and navigated through the page
4. ✅ Found the starting price (from a search result card)
5. ❌ But the selectors designed for vendor pages don't match the marketplace page structure

### Why This Happens

The selectors in `config.py` are designed for individual vendor pages:

```python
SELECTORS = {
    "vendor_name": [
        "h1.ods-c-text-hero-v1",           # Vendor page h1
        "[class*='text-hero--mp-']",
        ".vendor-name-container--mp-4b058 h1",
    ],
    "packages_section": [
        "[class*='pricesAndPackages--mp-']",  # Packages section on vendor page
        ".pricesAndPackages--mp-f70fc",
    ],
}
```

A marketplace listing page has:
- Multiple vendor cards (not a single h1 vendor name)
- Search result items (not a packages section)
- Links to individual vendor pages
- Filters, sorting, pagination

## Bot Detection Status

### Signs of NO Bot Detection:

1. ✅ **Successful navigation** - The page loaded completely
2. ✅ **Cookies working** - Session persistence is functioning
3. ✅ **Long interaction time** - Scraper ran for ~4 minutes without being blocked
4. ✅ **Partial data extraction** - Found pricing information
5. ✅ **No CAPTCHA warnings** in logs
6. ✅ **No block detection** warnings

### What Would Indicate Bot Detection:

- ❌ Access denied or 403 errors
- ❌ Immediate redirects to CAPTCHA pages
- ❌ Empty page content
- ❌ "unusual traffic" messages
- ❌ Connection refused/timeout
- ❌ JavaScript challenges not loading

**Conclusion: This is NOT a bot detection issue. The selectors simply don't match the page structure.**

## Solutions

### Solution 1: Use the Correct URL Type (Recommended)

Change the URL to an actual vendor page, for example:
```
https://www.theknot.com/marketplace/some-photographer-name-fishers-in
```

Individual vendor pages will have:
- A single business name (h1)
- Packages and pricing sections
- Business details
- Reviews

### Solution 2: Add Marketplace Scraping Functionality

If you want to scrape the marketplace listing page, you need to:

1. **Add new selectors for marketplace pages:**
```python
SELECTORS = {
    # ... existing selectors ...

    # Marketplace/Search Results selectors
    "search_result_cards": [
        "[class*='vendor-card']",
        "[data-testid='vendor-card']",
        ".search-result-item",
    ],
    "vendor_card_name": [
        "[class*='vendor-card'] h3",
        "[class*='vendor-card'] .vendor-name",
    ],
    "vendor_card_link": [
        "[class*='vendor-card'] a[href*='/marketplace/']",
        ".vendor-card-link",
    ],
}
```

2. **Add a method to extract vendor URLs from marketplace pages:**
```python
def scrape_marketplace_page(self, url: str) -> List[str]:
    """Extract individual vendor URLs from marketplace listing page"""
    # Navigate and find all vendor cards
    # Extract href links to individual vendor pages
    # Return list of vendor URLs
```

3. **Then scrape each individual vendor page:**
```python
marketplace_url = "https://www.theknot.com/marketplace/wedding-photographers-fishers-in"
vendor_urls = scraper.scrape_marketplace_page(marketplace_url)

for vendor_url in vendor_urls:
    vendor_data = scraper.scrape_vendor_page(vendor_url)
```

### Solution 3: Implement Page Type Detection

Add automatic detection of page type:

```python
def detect_page_type(self) -> str:
    """Detect if current page is marketplace or vendor page"""

    # Check URL pattern
    url = self.driver.current_url
    if '/marketplace/' in url:
        # Count slashes after /marketplace/
        parts = url.split('/marketplace/')[-1].split('/')

        if len(parts) == 1:
            # e.g., /marketplace/wedding-photographers-fishers-in
            return "marketplace_listing"
        else:
            # e.g., /marketplace/photographer-name-city-state
            return "vendor_page"

    return "unknown"
```

## Recommended Action Plan

1. **Short-term fix:**
   - Update `run.py` to use an actual vendor page URL
   - Or extract vendor URLs from saved HTML first

2. **Medium-term enhancement:**
   - Implement marketplace page scraping
   - Add automatic vendor URL extraction
   - Chain marketplace → vendor scraping

3. **Long-term improvement:**
   - Add page type detection
   - Implement different scraping strategies per page type
   - Add pagination support for marketplace pages

## Next Steps

1. Check the saved HTML/screenshot to identify actual vendor URLs
2. Either:
   - **Option A:** Update the URL in `run.py` to a real vendor page
   - **Option B:** Implement marketplace scraping to extract vendor URLs first
3. Re-run the scraper with the correct page type
4. Monitor for actual bot detection signs (if any)

## Summary

**This is NOT a bot detection problem.** The scraper is working correctly at the browser/network level. The issue is architectural:
- Using marketplace page URL with vendor page selectors
- Need to either use correct URL or implement marketplace scraping

The anti-detection measures (undetected-chromedriver, cookie persistence, human behavior simulation) are all functioning properly.
