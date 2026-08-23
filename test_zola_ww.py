"""
Quick access test for Zola and WeddingWire with Playwright
"""
import asyncio, os
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def test_source(name, url):
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        page = await context.new_page()
        
        print(f"\n{'='*60}")
        print(f"TESTING: {name}")
        print(f"{'='*60}")
        print(f"URL: {url}")
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            title = await page.title()
            content = await page.content()
            
            print(f"Title: {title}")
            print(f"HTML: {len(content):,} chars")
            
            # Check for blocking
            body_text = await page.inner_text('body') if await page.query_selector('body') else ''
            blocks = [kw for kw in ['403', 'forbidden', 'access denied', 'blocked', 'captcha', 'unusual traffic']
                     if kw in body_text.lower()]
            if blocks:
                print(f"❌ BLOCKED: {blocks}")
            else:
                print(f"✅ Page accessible")
            
            # Check for __NEXT_DATA__ (Next.js sites)
            next_data = await page.evaluate('() => document.getElementById("__NEXT_DATA__")?.textContent || null')
            if next_data:
                print(f"✅ __NEXT_DATA__ found ({len(next_data):,} chars)")
            else:
                print(f"❌ No __NEXT_DATA__")
            
            # Check for __INITIAL_STATE__ (Redux sites)
            init_state = await page.evaluate('() => typeof window.__INITIAL_STATE__ !== "undefined" ? "YES" : null')
            if init_state:
                print(f"✅ __INITIAL_STATE__ found")
            
            # Check for __APOLLO_STATE__ (Apollo/GraphQL sites)
            apollo = await page.evaluate('() => typeof window.__APOLLO_STATE__ !== "undefined" ? "YES(" + Object.keys(window.__APOLLO_STATE__).length + " keys)" : null')
            if apollo:
                print(f"✅ __APOLLO_STATE__: {apollo}")
            
            # Check for Hypernova
            hypernova = await page.evaluate('() => document.querySelector("[data-hypernova-key]")?.textContent ? "YES" : null')
            if hypernova:
                print(f"✅ Hypernova data found")
            
            # Check for vendor cards
            vendor_count = await page.evaluate('() => document.querySelectorAll("[class*=\"vendor\"], [class*=\"Vendor\"], [data-testid*=\"vendor\"]").length')
            print(f"Vendor elements on page: {vendor_count}")
            
            # Check bot detection
            for svc in ['cloudflare', 'datadome', 'perimeterx', 'akamai']:
                if svc in content.lower():
                    print(f"⚠️ {svc.upper()} detected in HTML")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        await browser.close()

# Test Zola
asyncio.run(test_source("Zola", "https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers"))

# Test WeddingWire
asyncio.run(test_source("WeddingWire", "https://www.weddingwire.com/wedding-photographers"))