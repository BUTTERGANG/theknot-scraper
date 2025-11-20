# Testing Guide for TheKnot Scraper

This guide walks you through testing the scraper to verify it can bypass TheKnot's bot detection.

## Prerequisites

Before testing, ensure you have:
- ✅ Python 3.8+ installed
- ✅ Chrome or Chromium browser installed
- ✅ All dependencies installed (`pip install -r requirements.txt`)
- ✅ Good internet connection
- ⚠️ **Ideally**: A residential IP address (not datacenter/VPN)

## Step 1: Validate Setup

First, validate that everything is installed correctly:

```bash
cd theknot_scraper
python validate_setup.py
```

Expected output:
```
======================================================================
VALIDATION SUMMARY
======================================================================

✅ PASS  Python Version
✅ PASS  Required Packages
✅ PASS  Scraper Modules
✅ PASS  Directories
✅ PASS  Chrome Browser

🎉 All checks passed! The scraper is ready to use.
```

If any checks fail, follow the suggestions to fix them.

## Step 2: Run the HTML Fetch Test

This test will attempt to fetch HTML from TheKnot.com:

```bash
python test_fetch_html.py
```

### What to Expect

The test will:

1. **Launch Chrome Browser** - A Chrome window will open (NOT headless)
2. **Navigate to TheKnot.com** - The browser will load the homepage
3. **Simulate Human Behavior** - You'll see:
   - Mouse movements (cursor moving)
   - Page scrolling
   - Random delays (looks like a human browsing)
4. **Fetch HTML** - Extract the page source
5. **Analyze Results** - Check for bot detection indicators

### Timeline

- **Total time**: 15-30 seconds
- **Navigation**: 3-5 seconds
- **Behavior simulation**: 5-10 seconds
- **Analysis**: 1-2 seconds

### Successful Test Output

```
======================================================================
TheKnot Scraper - HTML Fetch Test
Testing bot detection bypass capabilities
======================================================================

TEST 1: Fetch TheKnot.com Homepage
======================================================================

✅ SUCCESS: HTML fetched successfully!

HTML Analysis:
  - Length: 245,832 characters
  - Has <title>: True
  - Has <body>: True
  - Has content (>10KB): True

Bot Detection Indicators:
  - 403 error: False
  - 'Forbidden' text: False
  - 'Access Denied': False
  - 'Blocked' text: False
  - CAPTCHA detected: False

✅ SUCCESS: Successfully bypassed bot detection!

HTML saved to: output/theknot_homepage_20251120_143022.html
```

### Failed Test - Blocked

If you're blocked, you'll see:

```
Bot Detection Indicators:
  - 403 error: True
  - 'Forbidden' text: True
  - 'Blocked' text: True

❌ FAILURE: Page indicates we were BLOCKED
```

### Failed Test - CAPTCHA

If you hit a CAPTCHA:

```
Bot Detection Indicators:
  - CAPTCHA detected: True

❌ FAILURE: CAPTCHA challenge detected
(This may require manual solving)
```

**What to do**: The browser will stay open for 60 seconds. Solve the CAPTCHA manually, then the script will continue.

## Step 3: Analyze Results

After the test, check these files:

### 1. HTML Files

```bash
ls -lh output/*.html
```

Open the HTML file in a browser:

```bash
# Linux
xdg-open output/theknot_homepage_*.html

# Mac
open output/theknot_homepage_*.html

# Windows
start output/theknot_homepage_*.html
```

**What to look for:**
- ✅ **Good**: You see TheKnot's actual homepage with venues, vendors, etc.
- ❌ **Bad**: You see "Access Denied", "403 Forbidden", or CAPTCHA page

### 2. Screenshots

```bash
ls -lh output/*.png
```

Screenshots show what the browser saw. Compare with the HTML to verify.

### 3. Logs

```bash
cat logs/scraper.log
```

Look for:
- `Navigation successful` - Good sign
- `Page indicates we are blocked` - You were detected
- `CAPTCHA detected` - Challenge appeared

## Step 4: Test with Real Vendor Page

Once the homepage test passes, try a real vendor page:

1. Go to https://www.theknot.com in your regular browser
2. Search for vendors (e.g., "wedding venues in New York")
3. Click on a vendor
4. Copy the URL (e.g., `https://www.theknot.com/marketplace/venue-name-city-123456`)
5. Edit `test_fetch_html.py` and update the vendor URL in `test_vendor_page()`
6. Run the test again

## Troubleshooting

### ❌ Test Failed: Blocked Immediately

**Symptoms:**
- 403 Forbidden
- "Access Denied"
- Blocked in < 5 seconds

**Likely causes:**
1. Using datacenter IP (AWS, DigitalOcean, etc.)
2. Using known VPN IP
3. IP previously flagged

**Solutions:**
- ✅ Use residential proxy
- ✅ Try from home internet connection
- ✅ Increase delays: `min_delay=5.0, max_delay=10.0`
- ✅ Wait a few hours and retry

### ❌ Test Failed: CAPTCHA Challenge

**Symptoms:**
- CAPTCHA appears on page
- Script waits for manual solving

**Solutions:**
- ✅ Solve CAPTCHA manually (script waits 60s)
- ✅ Reduce request rate
- ✅ Use different IP
- ✅ Configure CAPTCHA solving service

### ❌ Test Failed: Headless Detection

**Symptoms:**
- Works with `headless=False`
- Fails with `headless=True`

**Solution:**
- ✅ Always use `headless=False` (visible browser)
- TheKnot detects headless browsers very effectively

### ❌ Test Failed: Timeout

**Symptoms:**
- "Timeout loading page"
- Takes >30 seconds

**Solutions:**
- ✅ Check internet connection
- ✅ Increase timeout: `page_load_timeout=60`
- ✅ Try different URL

### ❌ ChromeDriver Issues

**Symptoms:**
- "ChromeDriver not found"
- "Chrome version mismatch"

**Solutions:**
```bash
# Update Chrome
sudo apt update && sudo apt upgrade google-chrome-stable  # Linux
# or download latest from google.com/chrome

# Reinstall undetected-chromedriver
pip install --upgrade --force-reinstall undetected-chromedriver
```

## Configuration for Different Scenarios

### Maximum Stealth (Recommended)

```python
config = ScraperConfig(
    headless=False,           # CRITICAL
    min_delay=5.0,            # Slower
    max_delay=10.0,
    enable_mouse_movement=True,
    enable_random_scrolling=True,
    save_screenshots=True,
    log_level="INFO"
)
```

### With Residential Proxy

```python
config = ScraperConfig(
    headless=False,
    proxy="http://user:pass@proxy.example.com:8080",  # Your proxy
    min_delay=3.0,
    max_delay=6.0,
    # ... other settings
)
```

### Debug Mode (Troubleshooting)

```python
config = ScraperConfig(
    headless=False,
    min_delay=2.0,
    max_delay=4.0,
    save_screenshots=True,
    save_html=True,           # Save HTML for inspection
    log_level="DEBUG"         # Verbose logging
)
```

## Success Metrics

### Expected Success Rates

| Configuration | Success Rate | Notes |
|---------------|--------------|-------|
| Visible + Residential IP + Delays | 90-95% | Best setup |
| Visible + Home IP + Delays | 80-90% | Good |
| Visible + Datacenter IP | 40-60% | May be blocked |
| Headless + Any IP | 10-30% | Not recommended |

### What "Success" Looks Like

✅ **Full Success:**
- HTML fetched (>100KB)
- No 403/blocked messages
- No CAPTCHA
- Actual page content visible
- Title matches expected

✅ **Partial Success (with CAPTCHA):**
- CAPTCHA appears but can be solved manually
- After solving, page loads correctly

❌ **Failure:**
- Immediate 403 Forbidden
- "Access Denied" page
- Empty or minimal HTML
- Unsolvable CAPTCHA loop

## Next Steps After Successful Test

Once you can successfully fetch HTML:

1. **Inspect HTML Structure**
   - Open saved HTML file
   - Find vendor information elements
   - Identify CSS selectors for data

2. **Update Selectors**
   - Edit `config.py`
   - Update `SELECTORS` dictionary
   - Test extraction with real pages

3. **Test Data Extraction**
   ```bash
   python example_single_vendor.py
   ```

4. **Scale Up**
   - Start with 5-10 vendors
   - Monitor success rate
   - Adjust delays if needed

## Monitoring During Production

When scraping multiple vendors:

### Watch For:

- **Success rate drops** - May need to adjust delays or rotate IP
- **Increased CAPTCHAs** - Slow down request rate
- **403 errors** - IP may be flagged, rotate or wait
- **Empty extractions** - Selectors may have changed

### Best Practices:

- ✅ Start slow (5-10 vendors)
- ✅ Monitor logs continuously
- ✅ Take breaks between batches
- ✅ Keep success rate >80%
- ✅ Respect rate limits

## Testing Checklist

Before going to production:

- [ ] Validation script passes
- [ ] Homepage fetch test passes
- [ ] Vendor page fetch test passes
- [ ] HTML contains expected content
- [ ] Screenshots show actual pages
- [ ] Logs show successful navigation
- [ ] No blocks or CAPTCHAs
- [ ] Data extraction works (if testing that)
- [ ] Tested with 3-5 different vendors
- [ ] Rate limiting configured appropriately

## Getting Help

If tests continue to fail:

1. **Check logs**: `cat logs/scraper.log`
2. **Review screenshots**: Open images in `output/`
3. **Verify HTML**: Open HTML files in browser
4. **Try different IP**: Use home internet or residential proxy
5. **Increase delays**: Try `min_delay=10.0`
6. **Check recent updates**: TheKnot may have changed their detection

---

**Good luck with testing!** 🎉

Remember: Slower is better. Patient scraping with proper delays will always outperform fast, aggressive scraping.
