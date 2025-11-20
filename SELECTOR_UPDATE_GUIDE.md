# Selector Update Guide - Real Vendor Page Analysis

**Target URL:** https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212

---

## 🎯 Quick Start

You have **3 options** to update the selectors:

### Option 1: Automated Analysis (Recommended) ✅

```bash
cd theknot_scraper
python analyze_vendor_html.py
```

This script will:
1. Launch Chrome and fetch the real HTML
2. Analyze the structure automatically
3. Suggest selector updates
4. Save HTML for manual inspection

**Time:** ~2-3 minutes

---

### Option 2: Manual Browser Inspection 🔍

1. Open the vendor page in Chrome
2. Press F12 to open DevTools
3. Right-click elements → Inspect
4. Copy class names and data attributes
5. Update `config.py` manually

See: `theknot_scraper/MANUAL_SELECTOR_UPDATE.md` for detailed steps

**Time:** ~5-10 minutes

---

### Option 3: Share HTML With Me 📤

Just copy and share:
- The class name of the vendor name element (h1)
- The class name of the starting price element
- The class names for packages section

I'll update the selectors for you!

**Time:** ~1 minute

---

## 📁 Files Created

### theknot_scraper/analyze_vendor_html.py
Automated HTML analyzer that:
- Fetches HTML using the scraper
- Finds vendor name, pricing, and packages sections
- Analyzes class patterns and structure
- Suggests selector updates
- Saves HTML and analysis to `output/`

**Usage:**
```bash
cd theknot_scraper
python analyze_vendor_html.py
```

**Output:**
- `output/vendor_page_analysis.html` - Full HTML for inspection
- `output/selector_analysis.json` - Structured analysis
- Console output with suggested selectors

---

### theknot_scraper/MANUAL_SELECTOR_UPDATE.md
Step-by-step guide for manual inspection including:
- How to use Chrome DevTools
- What to look for in the HTML
- How to update config.py
- Common class name patterns
- Troubleshooting tips

---

## 🔧 What Needs Updating

Currently the selectors in `config.py` are generic placeholders:

```python
SELECTORS = {
    "vendor_name": [
        "h1.vendor-name",           # ← Generic placeholder
        "[data-testid='vendor-name']",
        "h1.storefrontHeader-title",
        "h1",
    ],
    "starting_price": [
        "[data-testid='starting-price']",
        ".starting-price",          # ← Generic placeholder
        ".price-display",
    ],
    # ... etc
}
```

**They need to be updated with the ACTUAL class names** from the real page.

---

## 🎨 Expected Structure

Based on modern React/TheKnot patterns, expect something like:

```html
<!-- Vendor Name -->
<h1 class="StorefrontHeader_title__abc123" data-testid="vendor-name">
    Original Weddings Photo and Video
</h1>

<!-- Starting Price -->
<div class="VendorPricing_startingPrice__xyz789">
    <span>Starting at</span>
    <strong>$2,500</strong>
</div>

<!-- Packages -->
<section class="PackageList_container__def456">
    <div class="PackageCard_wrapper__ghi789">
        <h3 class="PackageCard_title__jkl012">Basic Package</h3>
        <span class="PackageCard_price__mno345">$1,500</span>
        <div class="PackageCard_description__pqr678">
            Includes 6 hours of coverage...
        </div>
    </div>
</section>
```

**Class patterns:**
- `ComponentName_element__hash` (CSS Modules pattern)
- `vendor-*`, `storefront-*`, `package-*` (semantic naming)
- `[data-testid="..."]` (React Testing Library)

---

## 🚀 Testing Your Updates

After updating selectors:

```bash
# Test with the example script
cd theknot_scraper
python example_single_vendor.py
```

The script now uses the real vendor URL: `original-weddings-photo-and-video-seattle-wa-1088212`

**Expected Output:**
```
Business Name: Original Weddings Photo and Video
Starting Price: From $2,500
Packages Found: 3

Package #1:
  Name: Basic Package
  Price: $1,500
  Description: Includes 6 hours of coverage...

Success: True
```

---

## 🐛 Troubleshooting

### Issue: "Cannot find vendor name"

**Possible causes:**
- Selector doesn't match actual class name
- Name is loaded via JavaScript (wait longer)
- Name is in a different element (not h1)

**Debug:**
1. Check `output/vendor_page_analysis.html`
2. Search for the actual business name in HTML
3. Update selector with actual class name

---

### Issue: "Cannot find starting price"

**Possible causes:**
- Price is "Contact for pricing" (no actual number)
- Price is in a hidden element initially
- Price format is different than expected

**Debug:**
1. Check if "$" symbol appears in HTML
2. Look for "contact" or "request quote" instead
3. Update parser to handle different formats

---

### Issue: "Cannot find packages"

**Possible causes:**
- Packages are in a tab (need to click first)
- Packages are lazy-loaded on scroll
- Different vendors have different structures

**Debug:**
1. Check if packages section exists in HTML
2. Try scrolling to packages section first
3. Look for accordion/tab container

---

## 📋 Example Workflow

### Using Automated Analyzer:

```bash
# 1. Run analyzer
cd theknot_scraper
python analyze_vendor_html.py

# Wait for Chrome to open and fetch page (15-30 seconds)

# 2. Review output
cat output/selector_analysis.json

# 3. Open HTML file in browser to verify
open output/vendor_page_analysis.html  # Mac
# or
xdg-open output/vendor_page_analysis.html  # Linux

# 4. Update config.py with suggested selectors
nano config.py

# 5. Test
python example_single_vendor.py
```

---

### Using Manual Inspection:

```bash
# 1. Open page in browser
# Navigate to: https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212

# 2. Inspect elements (F12)
# Right-click vendor name → Inspect
# Note: class="StorefrontHeader_title__abc123"

# 3. Update config.py
nano theknot_scraper/config.py

# Add to vendor_name selectors:
# "h1.StorefrontHeader_title__abc123",

# 4. Test
cd theknot_scraper
python example_single_vendor.py
```

---

## 💡 Pro Tips

### 1. Use Multiple Fallbacks
Always provide multiple selectors from most specific to least specific:

```python
"vendor_name": [
    "h1.StorefrontHeader_title__abc123",  # Most specific
    "[data-testid='vendor-name']",         # Data attribute
    "h1.vendor-name",                      # Semantic class
    "h1",                                  # Generic fallback
]
```

### 2. Check Data Attributes First
`data-testid` attributes are usually stable:

```html
<div data-testid="vendor-name">...</div>
```

These rarely change compared to CSS Module hashes.

### 3. Use Browser DevTools Copy Selector
1. Right-click element in DevTools
2. Copy → Copy selector
3. Paste into config.py (may need cleanup)

### 4. Test with Multiple Vendors
Different vendors may have slightly different structures. Test with 2-3 vendor pages.

---

## 📊 Selector Priority

Order selectors by reliability:

1. **Most Reliable:** `data-testid` attributes
2. **Reliable:** Semantic class names (`vendor-name`, `package-card`)
3. **Moderately Reliable:** CSS Module classes (have hashes)
4. **Fallback:** Generic tags (`h1`, `div.price`)

---

## ✅ Verification Checklist

After updating selectors:

- [ ] Vendor name extracts correctly
- [ ] Starting price extracts correctly (or shows "Contact for pricing")
- [ ] Packages section is found
- [ ] Package names extract
- [ ] Package prices extract
- [ ] Package descriptions extract
- [ ] No errors in logs
- [ ] Test with 2-3 different vendor pages

---

## 🆘 Need Help?

If you get stuck, share with me:

**Quick info:**
```
Vendor name class: [paste here]
Price class: [paste here]
Packages container class: [paste here]
```

**Or detailed info:**
- Screenshot of vendor page
- Screenshot of DevTools inspection
- Error messages from scraper
- Output/logs from analyzer script

I'll help you get the selectors working!

---

## 📝 Summary

**Goal:** Update selectors in `config.py` to match real TheKnot HTML structure

**Best Approach:** Run `python analyze_vendor_html.py` first

**Quick Approach:** Manual inspection with DevTools

**Alternative:** Share class names with me, I'll update

**Test:** Run `python example_single_vendor.py` after updates

---

**Ready to start?**

1. Pick an option above (automated or manual)
2. Follow the steps
3. Test the results
4. Let me know if you need help!

Good luck! 🚀
