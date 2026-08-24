"""
Intercept TheKnot's real review XHR/GraphQL request to capture the exact query
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def intercept():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Capture all request/response pairs
        captured = []
        
        async def on_response(resp):
            url = resp.url
            if 'reviews' in url or 'review' in url or 'graphql' in url:
                if 'analytics' not in url and 'assets' not in url and 'segment' not in url:
                    try:
                        req = resp.request
                        post_data = req.post_data
                        body = await resp.text()
                        status = resp.status
                        
                        # Check for actual review content
                        has_review = 'review' in body.lower() or 'rating' in body.lower()
                        has_text = '"text"' in body or '"title"' in body
                        
                        captured.append({
                            'url': url[:180],
                            'status': status,
                            'method': req.method,
                            'post_data': (post_data or '')[:3000],
                            'response_size': len(body),
                            'response_preview': body[:1500],
                            'has_review_text': has_review and has_text,
                        })
                    except:
                        pass
        
        page.on('response', on_response)
        
        # Load vendor page
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Try to trigger review loading - click "See all reviews" / review tab / click link
        # The page shows "2625 reviews" — try clicking on the reviews count
        clicked = await page.evaluate('''() => {
            const els = document.querySelectorAll('a, button, span');
            for (const el of els) {
                const t = (el.textContent || '').trim();
                if (t.includes('2625 review') || t.includes('2625 Reviews') || 
                    (t.includes('review') && t.includes('See all'))) {
                    el.click();
                    return t;
                }
            }
            // Try the reviews section header
            const headers = document.querySelectorAll('[class*="review"] h2, [class*="review"] a');
            for (const el of headers) {
                if (el.textContent && el.textContent.toLowerCase().includes('review')) {
                    el.click();
                    return 'header: ' + el.textContent.trim();
                }
            }
            return null;
        }''')
        print(f"Clicked: {clicked}")
        await asyncio.sleep(3)
        
        # If a new page opened (new tab), handle it
        pages = ctx.pages
        if len(pages) > 1:
            page = pages[-1]
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(3)
            print(f"\nNew page opened: {page.url}")
            
            # Look for review data in the new page
            review_content = await page.evaluate('''() => {
                const results = [];
                document.querySelectorAll('[class*="review"], [data-testid*="review"]').forEach(el => {
                    const text = (el.textContent || '').trim();
                    if (text.length > 80) {
                        results.push({cls: (el.className || '').slice(0, 50), text: text.slice(0, 300)});
                    }
                });
                return results.slice(0, 5);
            }''')
            print(f"Review content in new page: {json.dumps(review_content, default=str)[:1000]}")
        
        # After any clicks, scroll and wait
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(3)
        
        # Print captured review API calls
        review_apis = [c for c in captured if c['has_review_text'] or 'reviews' in c['url'] or 'graphql' in c['url']]
        print(f"\n=== CAPTURED REVIEW-SPECIFIC NETWORK CALLS ({len(captured)}) ===")
        
        for c in captured:
            print(f"\n  [{c['method']}] [{c['status']}] {c['url']}")
            print(f"  Size: {c['response_size']} | hasReview: {c['has_review_text']}")
            if c['post_data'] and 'reviews' in c['url'].lower() or 'graphql' in c['url'].lower():
                print(f"  POST body: {c['post_data'][:2000]}")
            if c['has_review_text']:
                print(f"  Response preview: {c['response_preview'][:1500]}")

        await browser.close()

asyncio.run(intercept())