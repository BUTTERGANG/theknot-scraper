"""
Find the actual API endpoints that load review data for each source
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

async def find_review_apis():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Track XHR/FETCH requests that look like review APIs
        review_calls = []
        
        async def intercept_request(req):
            url = req.url
            # Filter to likely API calls
            if any(x in url for x in ['/api/', 'graphql', 'gql', '/review', '/rating',
                                       'recommend', 'vendor', 'search', 'listings']):
                if not any(x in url for x in ['.js', '.css', '.png', '.jpg', '.svg', '.gif', '.woff', 'segment']):
                    try:
                        resp = await req.response()
                        status = resp.status if resp else '?'
                    except:
                        status = '?'
                    review_calls.append({
                        'url': url[:200],
                        'method': req.method,
                        'status': status,
                        'type': req.resource_type,
                    })
        
        page.on('request', intercept_request)
        
        # THEKNOT — load a vendor page, click reviews, scroll
        print("=== THEKNOT REVIEW API ===")
        await page.goto(
            'https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
            wait_until='domcontentloaded', timeout=30000
        )
        await asyncio.sleep(4)
        
        # Scroll down to try to trigger lazy-loaded reviews
        for i in range(5):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {i/5})')
            await asyncio.sleep(1)
        
        # Click any "read reviews" / "see all" buttons
        await page.evaluate('''() => {
            const buttons = document.querySelectorAll('a, button, [role="button"]');
            for (const btn of buttons) {
                const t = (btn.textContent || '').toLowerCase();
                if (t.includes('review') || t.includes('see all') || t.includes('read')) {
                    btn.click();
                    break;
                }
            }
        }''')
        await asyncio.sleep(3)
        
        # Try clicking the review pills
        await page.evaluate('''() => {
            const pills = document.querySelectorAll('[class*="review"]');
            for (const p of pills) {
                if (p.textContent && (p.textContent.includes('review') || p.textContent.includes('star'))) {
                    p.click();
                    break;
                }
            }
        }''')
        await asyncio.sleep(3)
        
        print(f"\n  API calls detected ({len(review_calls)}):")
        seen = set()
        for c in review_calls:
            key = c['url'][:120]
            if key not in seen:
                seen.add(key)
                print(f"  [{c['method']}] [{c['status']}] {c['url']}")
    
        # Filter to just review-related API calls
        review_apis = [c for c in review_calls if any(x in c['url'].lower() for x in ['review', 'rating', 'vrm', 'feedback'])]
        print(f"\n  Review-specific APIs ({len(review_apis)}):")
        for c in review_apis:
            print(f"    {c['url']}")
        
        # Check the DOM after all interactions for review elements
        print("\n  Checking DOM for review content after interactions:")
        review_content = await page.evaluate('''() => {
            const results = [];
            // Look for any review cards or comment blocks
            const reviewEls = document.querySelectorAll('[class*="review-card"], [class*="reviewCard"], [data-testid*="review"], [class*="comment"], [class*="testimonial"]');
            results.push({selector: 'review-card/card/data-testid', count: reviewEls.length});
            
            // Try to find ANY content with quote-like text
            const allEls = document.querySelectorAll('p, blockquote, [class*="quote"]');
            let found = 0;
            for (const el of allEls) {
                const t = (el.textContent || '').trim();
                if (t.length > 100 && !t.includes('cookie') && !t.includes('privacy') && !t.includes('Sign up')) {
                    found++;
                    if (found <= 2) {
                        results.push({text: t.substring(0, 200).replace(/\\s+/g, ' ')});
                    }
                }
            }
            results.push({paragraphs_found: found});
            
            // Check hidden divs that might have review data
            const hidden = document.querySelectorAll('[aria-hidden="true"], .hidden, [style*="display: none"]');
            let hiddenWithText = 0;
            hidden.forEach(el => {
                if ((el.textContent || '').length > 100) hiddenWithText++;
            });
            results.push({hidden_divs_with_content: hiddenWithText});
            
            return results;
        }''')
        print(f"  {json.dumps(review_content, default=str)[:1000]}")
        
        # Check for Redux store changes after interactions
        state = await page.evaluate('() => window.__INITIAL_STATE__')
        if state:
            vrm = state.get('vrm', {})
            print(f"\n  VRM state after interaction: {json.dumps(vrm, default=str)[:500]}")
        
        # Determine best approach for TheKnot reviews
        print(f"\n  === APPROACH ASSESSMENT ===")
        print(f"  TheKnot: Reviews loaded via JS interaction — intercept XHR or scroll+parse")
        
        # ZOLA
        print(f"\n\n=== ZOLA REVIEW API ===")
        await page.goto(
            'https://www.zola.com/wedding-vendors/wedding-photographers/the-talented-photographer-award-winning-photography',
            wait_until='domcontentloaded', timeout=30000
        )
        await asyncio.sleep(4)
        
        # Scroll and interact
        for i in range(3):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {i/3})')
            await asyncio.sleep(1.5)
        
        # Check for review section
        zola_reviews = await page.evaluate('''() => {
            const results = {};
            // Look for review section
            const sections = document.querySelectorAll('section, div[class*="section"]');
            for (const s of sections) {
                const t = (s.textContent || '').toLowerCase();
                if (t.includes('what couples love') || t.includes('review') && t.includes('rating')) {
                    results.section = {
                        tag: s.tagName,
                        class: (s.className || '').substring(0, 80),
                        text: s.textContent.substring(0, 500).replace(/\\s+/g, ' ')
                    };
                    break;
                }
            }
            
            // Tally review cards
            const reviewCards = document.querySelectorAll('[class*="review"], [class*="testimonial"], blockquote');
            results.reviewElements = reviewCards.length;
            
            // Sample
            const samples = [];
            document.querySelectorAll('p').forEach(p => {
                const t = (p.textContent || '').trim();
                if (t.length > 100 && !t.includes('cookie') && !t.includes('Zola')) {
                    samples.push(t.substring(0, 200));
                    if (samples.length >= 2) return;
                }
            });
            results.samples = samples;
            
            return results;
        }''')
        print(f"  Zola reviews: {json.dumps(zola_reviews, default=str)[:1000]}")
        
        # WEDDINGWIRE
        print(f"\n\n=== WEDDINGWIRE REVIEW API ===")
        await page.goto(
            'https://www.weddingwire.com/biz/southern-palms-studio-saint-augustine/51ec19bd45b74c48.html',
            wait_until='domcontentloaded', timeout=30000
        )
        await asyncio.sleep(4)
        
        # Scroll
        for i in range(3):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {i/3})')
            await asyncio.sleep(1.5)
        
        ww_reviews = await page.evaluate('''() => {
            const results = {};
            const sections = document.querySelectorAll('[class*="review"], [class*="rating"], section');
            for (const s of sections) {
                const t = (s.textContent || '').toLowerCase();
                if (t.includes('review') && (t.includes('star') || t.includes('rating'))) {
                    results.reviewSection = {
                        class: (s.className || '').substring(0, 80),
                        text: s.textContent.substring(0, 500).replace(/\\s+/g, ' ')
                    };
                    break;
                }
            }
            
            // Count review items  
            const reviewItems = document.querySelectorAll('[class*="review-item"], [class*="reviewCard"], [class*="feedback"]');
            results.reviewItems = reviewItems.length;
            
            if (reviewItems.length > 0) {
                results.sample = reviewItems[0].textContent.substring(0, 400).replace(/\\s+/g, ' ');
            }
            
            // Check for review loading mechanism
            const loadMore = document.querySelectorAll('a, button');
            let loadMoreFound = false;
            for (const btn of loadMore) {
                if ((btn.textContent || '').toLowerCase().includes('load') || 
                    (btn.textContent || '').toLowerCase().includes('more') ||
                    (btn.textContent || '').toLowerCase().includes('read')) {
                    loadMoreFound = true;
                    break;
                }
            }
            results.loadMoreButton = loadMoreFound;
            
            return results;
        }''')
        print(f"  WeddingWire reviews: {json.dumps(ww_reviews, default=str)[:1000]}")
        
        await browser.close()

asyncio.run(find_review_apis())