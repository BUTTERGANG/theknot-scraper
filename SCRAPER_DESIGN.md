# TheKnot.com Scraper - Design Document

## Overview

This document describes the design and architecture of the sophisticated web scraper built to extract vendor information from TheKnot.com while bypassing the multi-layered bot detection mechanisms identified in our security analysis.

## Design Goals

1. **Bypass Bot Detection** - Evade all identified detection mechanisms
2. **Reliability** - Consistently extract vendor data with high success rate
3. **Maintainability** - Easy to update selectors and configuration
4. **Scalability** - Handle single vendors or batch processing
5. **User-Friendly** - Simple API and clear documentation
6. **Ethical** - Include rate limiting and respect for target site

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                   User Application                      │
│              (example scripts, custom code)             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  TheKnotScraper                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Config    │  │ Driver Setup │  │  Navigation   │  │
│  │ Management  │  │  & Stealth   │  │  & Behavior   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │    Data     │  │    Error     │  │    Session    │  │
│  │ Extraction  │  │   Handling   │  │  Management   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Undetected ChromeDriver                    │
│           (Real Chrome Browser Instance)                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   TheKnot.com                           │
│              (Target Website)                           │
└─────────────────────────────────────────────────────────┘
```

### Module Breakdown

#### 1. Configuration Module (`config.py`)

**Responsibilities:**
- Define all configurable parameters
- Store CSS selectors and XPath expressions
- Browser options and preferences
- Environment variable integration

**Key Classes:**
- `ScraperConfig` - Pydantic model for type-safe configuration

**Key Constants:**
- `SELECTORS` - CSS selectors for target elements
- `XPATH_SELECTORS` - XPath alternatives
- `CHROME_ARGS` - Browser arguments for anti-detection
- `CHROME_PREFS` - Browser preferences

#### 2. Utilities Module (`utils.py`)

**Responsibilities:**
- Human behavior simulation functions
- Safe element finding with fallbacks
- Cookie and session management
- Detection checking (CAPTCHA, blocks)
- Data parsing and extraction helpers

**Key Functions:**

**Behavior Simulation:**
- `random_delay()` - Variable timing between actions
- `smooth_scroll()` - Realistic scrolling patterns
- `move_mouse_randomly()` - Mouse movement simulation
- `simulate_human_behavior()` - Combined behavior simulation

**Element Interaction:**
- `safe_find_element()` - Try multiple selectors with timeout
- `safe_find_elements()` - Find multiple elements robustly
- `extract_text()` - Safe text extraction with fallbacks

**Session Management:**
- `save_cookies()` - Persist browser cookies
- `load_cookies()` - Restore previous session

**Detection:**
- `check_for_captcha()` - Detect CAPTCHA challenges
- `check_for_block()` - Detect blocking/403 pages
- `wait_for_page_load()` - Ensure page fully loaded

**Helpers:**
- `parse_price()` - Extract numeric values from price text
- `save_screenshot()` - Debug screenshot capture
- `save_page_source()` - Save HTML for analysis

#### 3. Main Scraper Module (`scraper.py`)

**Responsibilities:**
- Orchestrate entire scraping workflow
- Manage browser lifecycle
- Apply anti-detection measures
- Extract and structure data
- Handle errors and retries

**Key Classes:**

**VendorData** (dataclass):
```python
@dataclass
class VendorData:
    url: str
    business_name: str
    starting_price: str
    starting_price_numeric: Optional[float]
    packages: List[Dict[str, str]]
    raw_packages_html: str
    scrape_timestamp: str
    success: bool
    error_message: str
```

**TheKnotScraper** (main class):

Methods:
- `__init__(config)` - Initialize with configuration
- `setup_driver()` - Create undetected Chrome instance
- `_apply_stealth_scripts()` - Inject anti-detection JavaScript
- `navigate_to_page(url)` - Navigate with human behavior
- `scrape_vendor_page(url)` - Extract vendor data
- `_extract_business_name()` - Find and extract business name
- `_extract_starting_price()` - Find and extract starting price
- `_extract_packages()` - Find and extract package information
- `scrape_multiple_vendors(urls)` - Batch processing
- `close()` - Cleanup browser resources

Context Manager Support:
```python
with TheKnotScraper(config) as scraper:
    data = scraper.scrape_vendor_page(url)
```

## Anti-Detection Strategy

### Layer 1: Network/TLS Level

**Challenge:** TLS fingerprinting, IP reputation

**Solution:**
- Use real Chrome browser (not headless HTTP clients)
- Proper TLS handshake via Chromium
- Proxy support for IP rotation
- Residential proxies recommended

### Layer 2: HTTP Headers

**Challenge:** Header fingerprinting, User-Agent validation

**Solution:**
- Real browser automatically sends proper headers
- Correct Sec-Fetch-* headers
- Consistent header ordering
- Realistic Accept headers

### Layer 3: Browser Environment

**Challenge:** navigator.webdriver detection, missing browser properties

**Solution:**
```javascript
// Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Add chrome runtime
window.navigator.chrome = {
    runtime: {},
};

// Fix permissions API
// Fix plugins array
// Fix languages
```

### Layer 4: JavaScript Fingerprinting

**Challenge:** Canvas, WebGL, Audio fingerprinting

**Solution:**
- Real Chrome browser provides consistent fingerprints
- Actual GPU rendering
- Real audio context
- Genuine font rendering

### Layer 5: Behavioral Analysis

**Challenge:** Mouse tracking, scroll patterns, timing analysis

**Solution:**
- Random delays between actions
- Smooth scrolling with variable speeds
- Random mouse movements
- Realistic interaction timing
- Page dwell time

### Layer 6: Session Consistency

**Challenge:** Cookie validation, session tracking

**Solution:**
- Persistent cookie storage
- Session reuse across requests
- Consistent browser fingerprint
- IP consistency (via proxy)

## Data Extraction Strategy

### Selector-Based Extraction

**Primary Method:** CSS Selectors
```python
SELECTORS = {
    "vendor_name": [
        "h1.vendor-name",
        "h1[data-testid='vendor-name']",
        "h1.storefrontHeader-title",
        # Multiple fallbacks
    ]
}
```

**Fallback Method:** XPath
```python
XPATH_SELECTORS = {
    "vendor_name": [
        "//h1[contains(@class, 'vendor-name')]",
        # Multiple fallbacks
    ]
}
```

### Extraction Process

1. **Try Primary Selectors** - CSS selectors with wait
2. **Try Fallback Selectors** - Additional CSS patterns
3. **Try XPath** - XPath alternatives
4. **Log Warning** - If all fail, log and continue
5. **Extract Text** - Multiple text extraction methods
6. **Parse/Validate** - Clean and validate extracted data

### Robust Element Finding

```python
def safe_find_element(driver, selectors, by=By.CSS_SELECTOR, timeout=10):
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            continue
    return None
```

## Error Handling Strategy

### Detection & Response

1. **Block Detection**
   - Check page for "403", "Access Denied"
   - Screenshot on detection
   - Return error in VendorData
   - Log for analysis

2. **CAPTCHA Detection**
   - Check for reCAPTCHA, hCaptcha, PerimeterX
   - Wait for manual solving (default: 60s)
   - Optional: Auto-solve with service
   - Continue after solving

3. **Timeout Handling**
   - Configurable page load timeout
   - Retry logic (optional)
   - Save state before retry

4. **Element Not Found**
   - Try multiple selectors
   - Log warnings
   - Continue with partial data
   - Mark success=False if critical data missing

### Logging Strategy

**Levels:**
- `DEBUG` - Detailed selector attempts, delays, mouse movements
- `INFO` - Navigation, extraction results, success/failure
- `WARNING` - Element not found, CAPTCHA detected, partial data
- `ERROR` - Blocks, exceptions, critical failures

**Outputs:**
- Console (color-coded)
- File (`logs/scraper.log` with rotation)

## Configuration Design

### Multi-Level Configuration

1. **Defaults** - Sensible defaults in code
2. **Config File** - `.env` file for deployment
3. **Environment Variables** - Override via `THEKNOT_*` vars
4. **Code** - Direct `ScraperConfig()` instantiation

**Priority:** Code > Env Vars > .env File > Defaults

### Key Configuration Categories

**Performance:**
- Timeouts
- Delays (min/max)
- Retry counts

**Behavior:**
- Mouse movement enable/disable
- Scrolling enable/disable
- Headless mode (not recommended)

**Output:**
- Screenshots
- HTML saving
- Log level
- Output directory

**Advanced:**
- Proxy configuration
- CAPTCHA solving
- Custom User-Agent
- Cookie persistence

## Testing Strategy

### Manual Testing

1. **Single Vendor**
   - Test with known vendor URL
   - Verify all data fields extracted
   - Check screenshots/logs

2. **Multiple Vendors**
   - Test with 3-5 vendors
   - Verify rate limiting works
   - Check success rate

3. **Error Conditions**
   - Test with invalid URL
   - Test with blocked IP (datacenter)
   - Test with intentional CAPTCHA trigger

### Selector Validation

- Periodically check if selectors still work
- Update `config.py` when TheKnot changes layout
- Test after updates

## Scalability Considerations

### Current Design

- Single-threaded (one browser instance)
- Sequential processing
- Suitable for: 1-100 vendors

### Future Enhancements for Scale

**Multi-Threading:**
```python
# Multiple browser instances
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(scrape_vendor, url) for url in urls]
```

**Distributed Queue:**
- Redis/RabbitMQ for task queue
- Multiple workers
- Centralized result storage

**Proxy Rotation:**
- Proxy pool management
- Automatic rotation on block
- Health checking

## Security & Ethics

### Rate Limiting

**Implemented:**
- Configurable delays between requests
- Random variation in timing
- Batch processing with breaks

**Recommended:**
- 5-10 seconds between vendors
- 5-minute breaks every 20-30 vendors
- No more than 100-200 vendors per day per IP

### Data Responsibility

**Best Practices:**
- Don't scrape personal user data
- Only scrape publicly available vendor information
- Don't resell data without permission
- Give attribution if using publicly

### Legal Compliance

**Considerations:**
- Review TheKnot Terms of Service
- Check robots.txt compliance
- Consider CFAA implications (US)
- Consider GDPR (EU)
- Seek legal advice for commercial use

## Maintenance Plan

### Regular Tasks

**Weekly:**
- Check success rate
- Review error logs
- Test random vendors

**Monthly:**
- Verify selectors still work
- Update dependencies
- Check for new detection methods

**As Needed:**
- Update selectors when site changes
- Add new detection countermeasures
- Performance optimization

### Monitoring Indicators

**Warning Signs:**
- Success rate drops below 70%
- Increased CAPTCHA frequency
- New error patterns in logs
- Selector failures

## Performance Metrics

### Success Criteria

- **Extraction Rate:** >90% for business name
- **Price Extraction:** >80%
- **Package Extraction:** >70%
- **Block Rate:** <10%
- **CAPTCHA Rate:** <20%

### Optimization Opportunities

1. **Selector Performance**
   - Order selectors by likelihood
   - Remove obsolete selectors
   - Add new patterns

2. **Timing Optimization**
   - Reduce delays if success rate high
   - Increase if getting blocked

3. **Resource Usage**
   - Headless mode for trusted IPs (risky)
   - Disable screenshots in production
   - Optimize logging

## Conclusion

This scraper is designed as a production-ready, maintainable solution that balances effectiveness, reliability, and ethical considerations. The modular architecture allows easy updates and extensions while the comprehensive anti-detection measures provide high success rates.

**Key Success Factors:**
1. Real browser (not headless)
2. Proper rate limiting
3. Residential proxies
4. Regular maintenance
5. Ethical usage

---

**Design Version:** 1.0
**Last Updated:** November 2025
**Status:** Production Ready
