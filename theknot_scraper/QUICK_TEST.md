# Quick Test Reference Card

## 🚀 One-Command Test

```bash
cd theknot_scraper && python test_fetch_html.py
```

## ✅ What Success Looks Like

```
✅ SUCCESS: Successfully bypassed bot detection!
HTML saved to: output/theknot_homepage_20251120_143022.html
```

## ❌ Common Failures & Fixes

| Problem | Fix |
|---------|-----|
| "403 Forbidden" | Use residential proxy or home IP |
| "CAPTCHA detected" | Solve manually (browser stays open 60s) |
| "Timeout" | Increase `page_load_timeout=60` |
| "ChromeDriver not found" | `pip install --upgrade undetected-chromedriver` |
| "No module named 'pydantic'" | `pip install -r requirements.txt` |

## 🔧 Quick Config Changes

### More Stealth (if getting blocked)
```python
config = ScraperConfig(
    headless=False,      # KEEP THIS
    min_delay=10.0,      # ← Increase from 3
    max_delay=15.0,      # ← Increase from 6
)
```

### Add Proxy
```python
config = ScraperConfig(
    proxy="http://user:pass@proxy.com:8080",
)
```

### Debug Mode
```python
config = ScraperConfig(
    log_level="DEBUG",
    save_html=True,
)
```

## 📊 Check Results

```bash
# View HTML
xdg-open output/*.html  # Linux
open output/*.html      # Mac

# View logs
cat logs/scraper.log

# View screenshots
ls output/*.png
```

## 🎯 Success Checklist

- [ ] `validate_setup.py` shows all ✅
- [ ] Chrome browser opens (NOT headless)
- [ ] Mouse cursor moves on page
- [ ] Page scrolls automatically
- [ ] HTML file >100KB
- [ ] No "403" or "Forbidden" in HTML
- [ ] Screenshots show real page

## 💡 Remember

**CRITICAL**: `headless=False` (visible browser required!)

**Slower = Better**: 5-10 second delays recommended

**Residential IPs**: Work best (home internet, not datacenter)

---

**Full docs**: See `TESTING.md` for complete guide
