# Manual Selector Update Guide

If you can't run the automated analyzer, follow these steps to manually update selectors.

## Option 1: Run the Automated Analyzer (Recommended)

```bash
cd theknot_scraper
python analyze_vendor_html.py
```

This will:
1. Fetch the HTML using the scraper
2. Analyze the structure
3. Suggest selector updates
4. Save HTML for manual inspection

---

## Option 2: Manual Inspection

### Step 1: Open the Page in Your Browser

1. Navigate to: https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212
2. Open Chrome DevTools (F12 or Right-click → Inspect)

### Step 2: Find the Vendor Name

1. Right-click on the vendor/business name at the top of the page
2. Select "Inspect" from the context menu
3. Look at the HTML element (likely an `<h1>` tag)
4. Note the **class names** or **data-testid** attribute

**Example:**
```html
<h1 class="vendor-storefront-header__title">Original Weddings Photo and Video</h1>
```

**What to copy:** `vendor-storefront-header__title`

### Step 3: Find the Starting Price

1. Right-click on where the price is displayed (e.g., "Starting at $2,500")
2. Select "Inspect"
3. Note the class name or data-testid of the price element

**Example:**
```html
<div class="vendor-pricing__starting-price">Starting at $2,500</div>
```

**What to copy:** `vendor-pricing__starting-price`

### Step 4: Find the Packages Section

1. Scroll to the packages/pricing section
2. Right-click on the packages container
3. Inspect and note:
   - The container class (wraps all packages)
   - Individual package item class
   - Package name class
   - Package price class

**Example:**
```html
<div class="vendor-packages">
    <div class="package-card">
        <h3 class="package-card__title">Basic Package</h3>
        <span class="package-card__price">$1,500</span>
    </div>
</div>
```

**What to copy:**
- Container: `vendor-packages`
- Item: `package-card`
- Name: `package-card__title`
- Price: `package-card__price`

---

## Step 3: Update config.py

Edit `theknot_scraper/config.py` and update the `SELECTORS` dictionary:

```python
SELECTORS = {
    "vendor_name": [
        "h1.vendor-storefront-header__title",  # ← ADD THE ACTUAL CLASS HERE
        "[data-testid='vendor-name']",
        "h1.vendor-name",
        "h1",  # Fallback
    ],

    "starting_price": [
        ".vendor-pricing__starting-price",  # ← ADD THE ACTUAL CLASS HERE
        "[data-testid='starting-price']",
        ".starting-price",
        ".price-display",
    ],

    "packages_section": [
        ".vendor-packages",  # ← ADD THE ACTUAL CONTAINER CLASS
        "[data-testid='packages-section']",
        ".packages-container",
        "#packages",
    ],

    "package_item": [
        ".package-card",  # ← ADD THE ACTUAL PACKAGE ITEM CLASS
        ".package-item",
        "[data-testid='package']",
    ],

    "package_name": [
        ".package-card__title",  # ← ADD THE ACTUAL NAME CLASS
        ".package-name",
        "h3.package-heading",
    ],

    "package_price": [
        ".package-card__price",  # ← ADD THE ACTUAL PRICE CLASS
        ".package-price",
        "[data-testid='package-price']",
    ],
}
```

**Important:** Put the most specific/reliable selectors first!

---

## Step 4: Test Your Changes

Run the single vendor example:

```bash
python example_single_vendor.py
```

Update the URL in `example_single_vendor.py` to:
```python
vendor_url = "https://www.theknot.com/marketplace/original-weddings-photo-and-video-seattle-wa-1088212"
```

---

## Option 3: Share HTML with Me

If you prefer, you can:

1. Open the vendor page in your browser
2. Right-click anywhere → "View Page Source"
3. Copy the HTML (or relevant sections)
4. Share it with me

**What I need:**
- The HTML section containing the vendor name (around the `<h1>` tag)
- The HTML section containing the starting price
- The HTML section containing the packages/pricing

**Or simpler:**
Just share the actual class names you found in DevTools, like:
```
Vendor name class: vendor-storefront-header__title
Price class: vendor-pricing__starting-price
Packages container: vendor-packages
Package item: package-card
```

---

## Common TheKnot Class Patterns

Based on typical React/modern web design, look for patterns like:

- `vendor-*` (e.g., `vendor-name`, `vendor-pricing`)
- `storefront-*` (e.g., `storefront-header`)
- `package-*` (e.g., `package-card`, `package-title`)
- `[data-testid="..."]` attributes (React testing library)
- BEM naming: `block__element--modifier`

---

## Troubleshooting

### "Cannot find vendor name"
- Check if the name is in an `<h1>` or `<h2>` tag
- Look for `data-testid` attributes
- Try broader selectors like just `h1` first

### "Cannot find pricing"
- Price might be loaded dynamically via JavaScript
- Look for elements containing "$" symbol
- Check if there's a "Contact for pricing" message instead

### "Cannot find packages"
- Packages section might be in a tab or accordion
- Try clicking/opening the pricing section first
- Check if packages are in an iframe

---

## Quick Verification Script

After updating selectors, test them quickly:

```python
from config import SELECTORS

print("Current selectors:")
for key, selectors in SELECTORS.items():
    print(f"\n{key}:")
    for sel in selectors:
        print(f"  - {sel}")
```

---

## Need Help?

If you're stuck, share:
1. Screenshot of the vendor page
2. The class names you found
3. Any error messages from the scraper

I can then help you update the selectors correctly!
