# TheKnot.com Web Scraper

A sophisticated web scraping solution designed to extract vendor information from TheKnot.com while bypassing multi-layered bot detection mechanisms identified in our comprehensive security analysis.

## ⚠️ Legal Disclaimer

This tool is provided for **educational and research purposes only**. Before using this scraper:

1. **Review TheKnot.com's Terms of Service** - Ensure your use case complies with their terms
2. **Respect robots.txt** - Check TheKnot's robots.txt file for allowed/disallowed paths
3. **Rate Limiting** - Always implement reasonable rate limits to avoid overwhelming their servers
4. **Consider Official APIs** - For commercial use, contact TheKnot for official API access
5. **Ethical Use** - Use this tool responsibly and ethically

**The authors are not responsible for any misuse of this tool.**

## 🎯 Features

### Anti-Detection Measures

Based on our [bot detection analysis](../theknot-bot-detection-report.md), this scraper implements:

- ✅ **Undetected ChromeDriver** - Avoids basic webdriver detection
- ✅ **TLS Fingerprint Matching** - Uses real browser for proper TLS handshake
- ✅ **JavaScript Fingerprint Evasion** - Patches navigator.webdriver and other detection points
- ✅ **Human Behavior Simulation** - Realistic mouse movements, scrolling, and timing
- ✅ **Browser Header Matching** - Proper Sec-Fetch-* headers and realistic header combinations
- ✅ **Session Management** - Cookie persistence and session consistency
- ✅ **Configurable Delays** - Random delays between actions and requests
- ✅ **CAPTCHA Handling** - Manual CAPTCHA solving support with wait timers

### Data Extraction

Extracts the following vendor information:
- Business/Vendor Name
- Starting Price (text and numeric)
- Packages Section (name, price, description for each package)
- Raw HTML of packages section for custom parsing

### Additional Features

- 📊 **Multiple Output Formats** - JSON, CSV support
- 📸 **Screenshot Capture** - Automatic screenshots on errors or for debugging
- 📝 **Comprehensive Logging** - Detailed logs with configurable levels
- 🔄 **Retry Logic** - Automatic retries on failures
- 🎛️ **Flexible Configuration** - Environment variables or config file
- 🌐 **Proxy Support** - HTTP/SOCKS proxy configuration

## 📋 Requirements

- Python 3.8+
- Chrome/Chromium browser installed
- Internet connection
- (Optional) Residential proxy for better success rate

## 🚀 Installation

### 1. Clone the Repository

```bash
cd theknot_scraper
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## 📖 Usage

### Basic Example - Single Vendor

```python
from theknot_scraper import TheKnotScraper, ScraperConfig

# Configure scraper
config = ScraperConfig(
    headless=False,  # Visible browser (recommended)
    enable_mouse_movement=True,
    enable_random_scrolling=True,
    min_delay=3.0,
    max_delay=6.0
)

# Scrape a vendor page
vendor_url = "https://www.theknot.com/marketplace/vendor-name-city-state-123456"

with TheKnotScraper(config) as scraper:
    vendor_data = scraper.scrape_vendor_page(vendor_url)

    print(f"Business: {vendor_data.business_name}")
    print(f"Starting Price: {vendor_data.starting_price}")
    print(f"Packages: {len(vendor_data.packages)}")
```

### Example Scripts

#### Single Vendor Scraping

```bash
python example_single_vendor.py
```

Edit `example_single_vendor.py` to set your target vendor URL.

#### Multiple Vendors Scraping

```bash
python example_multiple_vendors.py
```

Edit `example_multiple_vendors.py` to set your list of vendor URLs.

### Advanced Configuration

```python
from theknot_scraper import TheKnotScraper, ScraperConfig
from pathlib import Path

config = ScraperConfig(
    # Browser settings
    headless=False,
    window_size=(1920, 1080),

    # Timing
    min_delay=5.0,
    max_delay=10.0,
    page_load_timeout=30,

    # Behavior simulation
    enable_mouse_movement=True,
    enable_random_scrolling=True,

    # Proxy (optional)
    proxy="http://user:pass@proxy.example.com:8080",

    # Output
    output_dir=Path("./my_output"),
    save_screenshots=True,
    save_html=True,

    # Logging
    log_level="DEBUG",
    log_file=Path("./logs/debug.log"),

    # Session
    save_cookies=True,
    cookie_file=Path("./cookies/session.pkl")
)

scraper = TheKnotScraper(config)
```

## 🏗️ Architecture

### Project Structure

```
theknot_scraper/
├── __init__.py              # Package initialization
├── config.py                # Configuration and constants
├── scraper.py               # Main scraper class
├── utils.py                 # Utility functions
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── example_single_vendor.py # Single vendor example
├── example_multiple_vendors.py # Multiple vendors example
└── README.md                # This file

Generated directories:
├── output/                  # Scraped data, screenshots
├── logs/                    # Log files
└── cookies/                 # Saved browser cookies
```

### Key Components

#### 1. TheKnotScraper Class (`scraper.py`)

Main scraper class with methods:
- `setup_driver()` - Initialize undetected Chrome with stealth
- `navigate_to_page(url)` - Navigate with human behavior
- `scrape_vendor_page(url)` - Extract vendor data
- `scrape_multiple_vendors(urls)` - Batch scraping

#### 2. Configuration (`config.py`)

- `ScraperConfig` - Pydantic model for settings
- `SELECTORS` - CSS selectors for data extraction
- `XPATH_SELECTORS` - XPath alternatives
- `CHROME_ARGS` - Browser arguments for stealth

#### 3. Utilities (`utils.py`)

Helper functions:
- `random_delay()` - Human-like delays
- `smooth_scroll()` - Realistic scrolling
- `move_mouse_randomly()` - Mouse movement simulation
- `safe_find_element()` - Robust element finding
- `check_for_captcha()` - CAPTCHA detection
- `check_for_block()` - Block detection

## 🔧 Configuration Options

### Environment Variables

All settings can be configured via environment variables with the `THEKNOT_` prefix:

```bash
THEKNOT_HEADLESS=false
THEKNOT_MIN_DELAY=3.0
THEKNOT_MAX_DELAY=6.0
THEKNOT_PROXY=http://proxy:8080
THEKNOT_LOG_LEVEL=INFO
```

See `.env.example` for all available options.

### ScraperConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `headless` | bool | False | Run browser in headless mode (not recommended) |
| `window_size` | tuple | (1920, 1080) | Browser window size |
| `min_delay` | float | 2.0 | Minimum delay between actions (seconds) |
| `max_delay` | float | 5.0 | Maximum delay between actions (seconds) |
| `enable_mouse_movement` | bool | True | Simulate mouse movements |
| `enable_random_scrolling` | bool | True | Simulate scrolling behavior |
| `proxy` | str | None | Proxy URL |
| `save_screenshots` | bool | True | Save screenshots on errors |
| `save_cookies` | bool | True | Persist cookies between sessions |
| `log_level` | str | "INFO" | Logging level (DEBUG, INFO, WARNING, ERROR) |

See `config.py` for complete list.

## 📊 Output Formats

### VendorData Object

```python
{
    "url": "https://www.theknot.com/marketplace/...",
    "business_name": "Example Venue",
    "starting_price": "From $5,000",
    "starting_price_numeric": 5000.0,
    "packages": [
        {
            "package_number": 1,
            "name": "Basic Package",
            "price": "$3,000",
            "description": "Includes..."
        }
    ],
    "raw_packages_html": "<div class='packages'>...</div>",
    "scrape_timestamp": "2025-11-20 10:30:00",
    "success": true,
    "error_message": ""
}
```

### JSON Output

```bash
output/vendor_data.json          # Single vendor
output/vendors_20251120_103000.json  # Multiple vendors
```

### CSV Output

```bash
output/vendors_20251120_103000.csv    # Summary data
output/packages_20251120_103000.csv   # Detailed packages
```

## 🛡️ Anti-Detection Strategy

### Implemented Countermeasures

Based on our bot detection analysis, the scraper implements these countermeasures:

| Detection Method | Countermeasure | Effectiveness |
|------------------|----------------|---------------|
| TLS Fingerprinting | Real Chrome browser | ✅ High |
| User-Agent Filtering | Matches browser UA | ✅ High |
| navigator.webdriver | Patched via CDP | ✅ High |
| Browser Properties | Realistic navigator object | ✅ High |
| HTTP Headers | Proper Sec-Fetch-* headers | ✅ High |
| Mouse/Keyboard | Simulated movements | ⚠️ Medium |
| Behavioral Analysis | Random delays & scrolling | ⚠️ Medium |
| IP Reputation | Proxy support | ⚠️ Varies |
| Canvas/WebGL | Real browser rendering | ✅ High |

### Success Rate Factors

Success depends on:
1. **Browser Visibility** - Headless mode significantly reduces success (NOT recommended)
2. **Proxy Quality** - Residential proxies work best; datacenter IPs may be blocked
3. **Request Rate** - Slower is better; recommend 5-10 second delays
4. **Session Management** - Reusing cookies improves success
5. **Random Behavior** - Enabled mouse and scroll simulation helps

### Recommended Settings for Best Results

```python
config = ScraperConfig(
    headless=False,              # ⚠️ IMPORTANT: Don't use headless
    min_delay=5.0,               # Slower delays
    max_delay=10.0,
    enable_mouse_movement=True,  # Enable behavior simulation
    enable_random_scrolling=True,
    save_cookies=True,           # Reuse sessions
    proxy="residential_proxy"    # Use residential proxy if possible
)
```

## 🚨 Troubleshooting

### Common Issues

#### 1. 403 Forbidden / Blocked

**Symptoms:**
- Immediate 403 error
- "Access Denied" page
- Page loads but shows block message

**Solutions:**
- ✅ Ensure `headless=False`
- ✅ Use residential proxy instead of datacenter
- ✅ Increase delays between requests
- ✅ Clear cookies and start fresh session
- ✅ Check if IP is blacklisted

#### 2. CAPTCHA Challenges

**Symptoms:**
- CAPTCHA appears on page
- Script pauses and waits

**Solutions:**
- ✅ Solve CAPTCHA manually (scraper will wait)
- ✅ Use CAPTCHA solving service (set `auto_solve_captcha=True`)
- ✅ Reduce request rate
- ✅ Use different IP/proxy

#### 3. Element Not Found

**Symptoms:**
- Missing business name or price
- Empty packages list
- Warning logs about selectors

**Solutions:**
- ✅ Check if page structure changed (update SELECTORS in config.py)
- ✅ Enable `save_html=True` to inspect page source
- ✅ Verify vendor URL is correct
- ✅ Check if page fully loaded (increase `page_load_timeout`)

#### 4. ChromeDriver Issues

**Symptoms:**
- "ChromeDriver not found"
- Version mismatch errors
- Browser won't start

**Solutions:**
- ✅ Update Chrome browser to latest version
- ✅ Reinstall `undetected-chromedriver`: `pip install --upgrade undetected-chromedriver`
- ✅ Check Chrome is installed: `google-chrome --version` or `chromium --version`

### Debug Mode

Enable detailed logging:

```python
config = ScraperConfig(
    log_level="DEBUG",
    save_screenshots=True,
    save_html=True
)
```

Check logs in `logs/scraper.log`

## 📈 Performance & Rate Limiting

### Recommended Practices

1. **Rate Limiting**
   - Single vendor: 5-10 seconds between pages
   - Multiple vendors: 10-15 seconds between requests
   - Session break: Every 20-30 vendors

2. **Batch Processing**
   ```python
   # Process in batches
   batch_size = 10
   for i in range(0, len(all_urls), batch_size):
       batch = all_urls[i:i+batch_size]
       results = scraper.scrape_multiple_vendors(batch)
       time.sleep(300)  # 5-minute break between batches
   ```

3. **Proxy Rotation**
   - Rotate residential proxies every 10-20 requests
   - Use proxy services like BrightData, Oxylabs, or Smartproxy

4. **Session Management**
   - Reuse cookies to maintain session
   - Clear cookies if blocked
   - Simulate multiple "users" with different sessions

## 🔮 Future Enhancements

Potential improvements:

- [ ] Automatic CAPTCHA solving integration (2Captcha, Anti-Captcha)
- [ ] Playwright as alternative to Selenium
- [ ] Distributed scraping with task queue
- [ ] Search result scraping (in addition to direct vendor pages)
- [ ] Database integration for results storage
- [ ] Real-time monitoring dashboard
- [ ] ML-based selector detection (auto-adapt to page changes)
- [ ] Advanced proxy rotation management
- [ ] Headless mode improvements with better stealth

## 📚 Additional Resources

- [Bot Detection Analysis Report](../theknot-bot-detection-report.md)
- [Undetected ChromeDriver Documentation](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [TheKnot robots.txt](https://www.theknot.com/robots.txt)

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Better selector detection
- Additional anti-detection measures
- Performance optimization
- Documentation improvements

## 📄 License

This tool is provided as-is for educational and research purposes.

## ⚖️ Ethical Considerations

When using this scraper:

1. **Respect Server Load** - Use reasonable rate limits
2. **Personal Data** - Respect privacy; don't scrape personal information
3. **Commercial Use** - Consider TheKnot's business model; seek official API for commercial use
4. **Attribution** - Give credit if using scraped data publicly
5. **Legal Compliance** - Ensure compliance with local laws (CFAA, GDPR, etc.)

## 📞 Support

For issues:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review logs in `logs/scraper.log`
3. Enable DEBUG mode for detailed output
4. Check if selectors need updating

---

**Remember:** This tool is powerful but should be used responsibly. Always respect website terms of service and implement appropriate rate limiting.

**Happy (ethical) scraping! 🎉**
