# TheKnot Scraper - Bot Detection Analysis & Fixes

## Issue Analysis

### Original Problem

The scraper was failing with these symptoms:
```
WARNING  | Could not find business name
WARNING  | Could not find packages section
WARNING  | Scraping incomplete - no business name found
```

However, it did find:
```
INFO     | Found starting price: Starting at $1,695
```

### Root Cause: NOT Bot Detection

After thorough analysis, **this was NOT a bot detection issue**. The problem was:

**Using a marketplace listing URL with selectors designed for individual vendor pages.**

#### Evidence that bot detection was NOT active:
- ✅ Navigation successful
- ✅ Cookies loaded/saved properly
- ✅ 4+ minutes of scraping without blocks
- ✅ Partial data extraction (found pricing)
- ✅ No CAPTCHA warnings
- ✅ No access denied errors

#### The Real Issue:

The URL being scraped was:
```
https://www.theknot.com/marketplace/wedding-photographers-fishers-in
```

This is a **MARKETPLACE/SEARCH RESULTS page** showing multiple photographers, NOT an individual vendor page.

The selectors in `config.py` were designed for vendor pages with:
- Single business name (h1)
- Packages section
- Detailed business info

But marketplace pages have:
- Multiple vendor cards
- Search results
- Links to individual vendors
- No single business name or packages

## Fixes Implemented

### 1. Added Marketplace Page Detection (`scraper.py:345`)

New method `detect_page_type()` that:
- Analyzes URL structure (vendor URLs contain `--`)
- Examines page content (multiple cards = marketplace, single h1 = vendor)
- Returns: `"marketplace"`, `"vendor"`, or `"unknown"`

### 2. Added Marketplace Scraping (`scraper.py:396`)

New method `scrape_marketplace_page()` that:
- Extracts vendor URLs from marketplace/search pages
- Returns list of individual vendor page URLs
- Supports limiting number of results
- Saves debug info if no URLs found

### 3. Updated Selectors (`config.py:166`)

Added new selectors for marketplace pages:
```python
"search_result_cards": [...],  # Find vendor cards
"vendor_card_link": [...],     # Extract vendor URLs
"vendor_card_name": [...],     # Get vendor names from cards
```

### 4. Updated Main Runner (`run.py`)

Now intelligently:
- Detects page type automatically
- If marketplace: extracts vendor URLs, then scrapes first vendor as example
- If vendor: scrapes directly
- Provides helpful error messages and guidance

### 5. Added Example Script

New `example_marketplace_scraper.py` demonstrates:
- Extracting all vendor URLs from marketplace page
- Scraping each vendor individually
- Saving results to JSON
- Proper delays between requests

## Usage

### Option 1: Automatic Detection (Recommended)

```bash
# Works with both marketplace and vendor URLs
python run.py https://www.theknot.com/marketplace/wedding-photographers-fishers-in
python run.py https://www.theknot.com/marketplace/some-vendor-name-city--12345
```

The scraper will automatically:
1. Detect the page type
2. Use appropriate scraping strategy
3. Save results to `output/`

### Option 2: Marketplace Scraping

```bash
# Extract and scrape multiple vendors from marketplace
python theknot_scraper/example_marketplace_scraper.py
```

This will:
1. Extract all vendor URLs from the marketplace page
2. Scrape the first 3 vendors (configurable)
3. Save all results to `output/all_vendors_data.json`

### Option 3: Direct Vendor Scraping

```python
from theknot_scraper.scraper import TheKnotScraper
from theknot_scraper.config import ScraperConfig

config = ScraperConfig()
with TheKnotScraper(config) as scraper:
    # Scrape a specific vendor page
    vendor_data = scraper.scrape_vendor_page(
        "https://www.theknot.com/marketplace/vendor-name-city--12345"
    )
```

## What Changed

### Files Modified:
1. **`theknot_scraper/config.py`**
   - Added marketplace page selectors

2. **`theknot_scraper/scraper.py`**
   - Added `detect_page_type()` method
   - Added `scrape_marketplace_page()` method

3. **`run.py`**
   - Updated to detect page type
   - Handle both marketplace and vendor URLs
   - Better error messages

### Files Added:
1. **`theknot_scraper/example_marketplace_scraper.py`**
   - Complete example of marketplace → vendor scraping

2. **`BOT_DETECTION_ANALYSIS.md`**
   - Detailed analysis of the issue

3. **`SCRAPER_FIXES.md`** (this file)
   - Summary of changes and usage

## Bot Detection Status

The anti-detection measures are working correctly:
- ✅ `undetected-chromedriver` preventing automation detection
- ✅ Cookie persistence maintaining sessions
- ✅ Human behavior simulation (mouse, scrolling, delays)
- ✅ Stealth JavaScript injections hiding automation

No additional bot detection countermeasures are needed at this time.

## Testing the Fix

To verify the fixes work:

1. **Test marketplace page:**
   ```bash
   python run.py https://www.theknot.com/marketplace/wedding-photographers-fishers-in
   ```
   Should:
   - Detect as marketplace page
   - Extract vendor URLs
   - Scrape first vendor
   - Save `output/vendor_urls.json`

2. **Test vendor page:**
   ```bash
   python run.py <vendor-url-from-step-1>
   ```
   Should:
   - Detect as vendor page
   - Extract business name, price, packages
   - Mark as successful

3. **Test multiple vendors:**
   ```bash
   python theknot_scraper/example_marketplace_scraper.py
   ```
   Should:
   - Extract all vendor URLs
   - Scrape first 3 vendors
   - Save `output/all_vendors_data.json`

## Troubleshooting

### If no vendor URLs are found:

1. Check `output/marketplace_*.png` screenshot
2. Check `output/marketplace_*.html` for page structure
3. The website may have changed - update selectors in `config.py`

### If vendor scraping fails:

1. Verify URL is a vendor page (contains `--` in URL)
2. Check `output/vendor_page_*.png` screenshot
3. Website structure may have changed - update selectors

### If actual bot detection occurs:

Signs of real bot detection:
- Access denied / 403 errors
- CAPTCHA challenges
- Empty page content
- "Unusual traffic" messages

Solutions:
- Add proxies to `config.proxy`
- Increase delays in config
- Use residential proxies
- Implement CAPTCHA solving

## Summary

The original issue was **architectural, not bot detection**. The scraper is now enhanced to:

1. ✅ Automatically detect page types
2. ✅ Handle marketplace pages correctly
3. ✅ Extract vendor URLs from search results
4. ✅ Scrape individual vendors
5. ✅ Provide clear error messages
6. ✅ Save comprehensive debug info

The anti-detection measures continue to work effectively.
