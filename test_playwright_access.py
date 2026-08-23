"""
TheKnot access test v2 - robust version
"""
import asyncio
import os
import sys
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

BLOCKED_KEYWORDS = ['403', 'forbidden', 'access denied', 'blocked', 'unusual traffic',
                     'automated requests', 'bot detected', 'captcha', 'verify you are a human']

async def test_page(page, label, url, wait_for='networkidle'):
    print(f"\n[{label}] {url}")
    try:
        await page.goto(url, wait_until=wait_for, timeout=30000)
        title = await page.title()
        content = await page.content()
        
        print(f"  Title: {title[:100]}")
        print(f"  HTML: {len(content):,} chars")
        
        body_text = ''
        try:
            body_text = await page.inner_text('body')
        except:
            pass
        
        blocks = [kw for kw in BLOCKED_KEYWORDS if kw in body_text.lower()]
        if blocks:
            print(f"  ❌ BLOCKED: {blocks}")
            return False
        
        print(f"  ✅ Access OK")
        
        # Content analysis
        text_lc = body_text.lower() if body_text else ''
        
        # Check bot detection
        for svc, kw in [('PerimeterX', 'perimeterx'), ('DataDome', 'datadome'),
                        ('Cloudflare', 'cloudflare'), ('Akamai', 'akamai')]:
            if kw in content.lower():
                print(f"  ⚠️  {svc} present in HTML")
        
        # Extract vendor data
        vendor_links = await page.query_selector_all('a[href*="/marketplace/"][href*="--"]')
        print(f"  Vendor links: {len(vendor_links)}")
        
        # Sample a few vendor hrefs
        if vendor_links:
            hrefs = []
            for link in vendor_links[:5]:
                href = await link.get_attribute('href')
                if href:
                    hrefs.append(href)
            for h in hrefs[:3]:
                print(f"    -> {h[:100]}")
        
        # Look for structured data / JSON-LD
        jsonld = await page.query_selector_all('script[type="application/ld+json"]')
        print(f"  JSON-LD blocks: {len(jsonld)}")
        
        return True
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


async def main():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
            ),
            locale='en-US',
        )
        
        page = await context.new_page()
        
        print("=== THEKNOT ACCESS TEST v2 ===")
        
        # Test pages
        results = {}
        
        # Try homepage first with domcontentloaded (faster)
        print("\n--- Homepage ---")
        try:
            await page.goto('https://www.theknot.com/', wait_until='domcontentloaded', timeout=20000)
            title = await page.title()
            print(f"  Title: {title[:100]}")
            print(f"  Loaded with domcontentloaded")
        except Exception as e:
            print(f"  Homepage timeout: {e}")
            print(f"  (This is OK - marketplace pages work better)")
        
        # Marketplace main
        await test_page(page, "Marketplace", "https://www.theknot.com/marketplace")
        
        # Photographer search
        await test_page(page, "Photographers", "https://www.theknot.com/marketplace/wedding-photographers")
        
        # Try a specific city search  
        await test_page(page, "City Search", "https://www.theknot.com/marketplace/wedding-photographers-indianapolis-in")
        
        # Try to extract a vendor URL and scrape a specific vendor
        print("\n--- Vendor Detail Test ---")
        vendor_links = await page.query_selector_all('a[href*="/marketplace/"][href*="--"]')
        if vendor_links:
            href = await vendor_links[0].get_attribute('href')
            if href and not href.startswith('http'):
                href = 'https://www.theknot.com' + href
            print(f"  Scraping: {href}")
            if href:
                await test_page(page, "Vendor Detail", href, wait_for='domcontentloaded')
        
        await browser.close()
        print("\n=== TEST COMPLETE ===")

asyncio.run(main())