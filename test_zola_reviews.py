"""
Quick test of Zola review extraction on one vendor
"""
import asyncio, json, os, re
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def test_one():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        url = 'https://www.zola.com/wedding-vendors/wedding-photographers/the-talented-photographer-award-winning-photography'
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Scroll through whole page
        print("Scrolling...")
        for i in range(10):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/10})')
            await asyncio.sleep(1)
        
        # Try "Load more reviews" buttons
        for attempt in range(8):
            clicked = await page.evaluate('''() => {
                const btns = document.querySelectorAll('button, [role="button"]');
                for (const b of btns) {
                    const t = (b.textContent || '').toLowerCase();
                    if (t.includes('load more') || t.includes('more review') || t.includes('show more')) {
                        b.click();
                        return b.textContent.trim();
                    }
                    if (t.includes('view all') || t.includes('see all')) {
                        b.click();
                        return b.textContent.trim();
                    }
                }
                return null;
            }''')
            if clicked:
                print(f"  Clicked: {clicked}")
                await asyncio.sleep(2)
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
            else:
                break
        
        # Extract the full review text — get raw DOM
        reviews_raw = await page.evaluate('''() => {
            // Grab the reviews section outer HTML
            const sections = document.querySelectorAll('[class*="review"]');
            if (sections.length === 0) return [];
            
            const results = [];
            for (const el of sections) {
                const cls = (el.className || '');
                if (cls.includes('review') && cls.includes('section') || 
                    cls.includes('reviewsContent') || cls.includes('reviews__')) {
                    results.push({
                        cls: cls.slice(0, 60),
                        html: el.outerHTML.slice(0, 8000)
                    });
                }
            }
            return results.slice(0, 3);
        }''')
        
        print(f"\nFound {len(reviews_raw)} review sections")
        if reviews_raw:
            for r in reviews_raw[:2]:
                print(f"\n--- Section class: {r['cls']} ---")
                print(r['html'][:3000])
        
        # Also count review cards
        review_count = await page.evaluate('''() => {
            const cards = document.querySelectorAll('[class*="review"], [class*="testimonial"]');
            return cards.length;
        }''')
        print(f"\nTotal review-class elements: {review_count}")
        
        await browser.close()

asyncio.run(test_one())