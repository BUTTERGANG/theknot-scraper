# Quick Start Guide

Get started with TheKnot scraper in 5 minutes!

## 🚀 Installation

### Option 1: Automated Setup (Recommended)

```bash
./setup.sh
```

This will:
- Create virtual environment
- Install dependencies
- Create necessary directories
- Set up configuration

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p output logs cookies

# Copy environment file
cp .env.example .env
```

## 📝 Basic Usage

### 1. Single Vendor Example

Create a file `test.py`:

```python
from theknot_scraper import TheKnotScraper, ScraperConfig

# Configure
config = ScraperConfig(
    headless=False,  # IMPORTANT: Keep False for better success
    min_delay=3.0,
    max_delay=6.0
)

# URL of vendor to scrape
url = "https://www.theknot.com/marketplace/your-vendor-url"

# Scrape
with TheKnotScraper(config) as scraper:
    data = scraper.scrape_vendor_page(url)

    print(f"Business: {data.business_name}")
    print(f"Price: {data.starting_price}")
    print(f"Packages: {len(data.packages)}")
```

Run it:

```bash
python test.py
```

### 2. Use Example Scripts

```bash
# Edit the URL in the example file
nano example_single_vendor.py

# Run it
python example_single_vendor.py
```

## ⚙️ Configuration

Edit `.env` file to customize:

```bash
# Most important settings
THEKNOT_HEADLESS=false           # Keep as false!
THEKNOT_MIN_DELAY=3.0            # Increase for slower/safer
THEKNOT_MAX_DELAY=6.0
THEKNOT_SAVE_SCREENSHOTS=true    # Helpful for debugging
```

## 🎯 Find Vendor URLs

To get vendor URLs from TheKnot:

1. Go to https://www.theknot.com
2. Search for vendors (e.g., "wedding venues in Seattle")
3. Click on a vendor
4. Copy the URL from browser address bar

Example URL format:
```
https://www.theknot.com/marketplace/venue-name-seattle-wa-123456
```

## 📊 Output

Results are saved to `output/` directory:

- `vendor_data.json` - Scraped data in JSON
- `screenshots/` - Debug screenshots
- Logs in `logs/scraper.log`

## ⚠️ Troubleshooting

### Getting 403 Errors?

1. Make sure `headless=False`
2. Increase delays: `min_delay=5.0, max_delay=10.0`
3. Use a proxy (residential if possible)
4. Check if your IP is blocked

### CAPTCHA appears?

1. Solve it manually (scraper waits 60 seconds by default)
2. Reduce request rate
3. Use different IP/proxy

### No data extracted?

1. Check logs: `cat logs/scraper.log`
2. Enable debug: `log_level="DEBUG"`
3. Save HTML: `save_html=True` and inspect the page
4. Selectors may have changed - update in `config.py`

## 📚 Next Steps

- Read full [README.md](README.md) for detailed documentation
- Review [bot detection analysis](../theknot-bot-detection-report.md)
- Configure proxy for better results
- Set up CAPTCHA solving service (optional)

## 💡 Tips for Success

1. **Don't rush** - Slower is better
2. **Use visible browser** - headless=False
3. **Monitor logs** - Check for warnings
4. **Respect rate limits** - 5-10 seconds between requests
5. **Use proxy** - Residential proxy preferred
6. **Save cookies** - Reuse sessions

## 🆘 Need Help?

Check the troubleshooting section in [README.md](README.md#-troubleshooting)

---

Happy scraping! 🎉
