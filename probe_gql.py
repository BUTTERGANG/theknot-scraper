"""
Probe TheKnot GraphQL with correct headers + dive into DOM review data
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def probe():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Load a vendor page first
        await page.goto(
            'https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
            wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Get vendor ID
        vendor_id = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            return s?.vendor?.vendorRaw?.vendorId || s?.vendor?.vendor?.vendorId || '';
        }''')
        print(f"Vendor ID: {vendor_id}")
        
        # Try GraphQL with x-tenant-id
        print("\n=== GraphQL with x-tenant-id ===")
        gql_with_header = await page.evaluate('''async (vendorId) => {
            const query = {
                operationName: "GetVendorReviews",
                variables: { vendorId: vendorId, first: 5, after: null },
                query: `query GetVendorReviews($vendorId: ID!, $first: Int!, $after: String) {
                    vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                        edges { node { id rating title text createdAt reviewer { name } } }
                        pageInfo { hasNextPage endCursor totalCount }
                    }
                }`
            };
            try {
                const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "x-tenant-id": "theknot.com"
                    },
                    body: JSON.stringify(query)
                });
                const data = await resp.json();
                return JSON.stringify(data).slice(0, 5000);
            } catch(e) { return "ERROR: " + e.message; }
        }''', vendor_id)
        print(f"{gql_with_header[:3000]}")
        
        # DEEP DOM ANALYSIS — extract every review text available
        print("\n=== Full DOM review extraction ===")
        
        # Click through pagination / load more
        for click_attempt in range(3):
            clicked = await page.evaluate('''() => {
                const buttons = document.querySelectorAll('button, a, [role="button"]');
                for (const btn of buttons) {
                    const t = (btn.textContent || '').toLowerCase();
                    if (t.includes('load more') || t.includes('show more') || t.includes('see all') || t === 'reviews') {
                        btn.click();
                        return btn.textContent.trim();
                    }
                }
                return null;
            }''')
            if clicked:
                print(f"  Clicked: {clicked}")
                await asyncio.sleep(2)
            else:
                break
        
        # Now extract ALL review text
        all_reviews = await page.evaluate('''() => {
            const results = [];
            
            // Strategy 1: Find review cards directly
            const reviewCards = document.querySelectorAll('[class*="review-card"], [class*="reviewCard"], [class*="review-card"]');
            for (const card of reviewCards) {
                const text = (card.textContent || '').replace(/\\s+/g, ' ').trim();
                if (text.length > 50) {
                    results.push({ method: 'cards', text: text.slice(0, 500) });
                }
            }
            
            // Strategy 2: Find elements inside review section
            const reviewSections = document.querySelectorAll('[class*="review-snippet"], [class*="reviews-section"], [class*="reviewSection"]');
            for (const section of reviewSections) {
                const cards = section.querySelectorAll('[class*="card"], [class*="item"], div[class]');
                for (const card of cards) {
                    const text = (card.textContent || '').replace(/\\s+/g, ' ').trim();
                    if (text.length > 100 && text.length < 3000) {
                        results.push({ method: 'section-cards', text: text.slice(0, 500) });
                        if (results.length >= 5) break;
                    }
                }
                if (results.length >= 5) break;
            }
            
            // Strategy 3: Find review data in hidden/script elements
            document.querySelectorAll('script:not([src])').forEach(s => {
                const html = s.textContent || '';
                if (html.includes('"review"') && html.includes('rating')) {
                    try {
                        const data = JSON.parse(html);
                        results.push({ method: 'script-json', text: JSON.stringify(data).slice(0, 500) });
                    } catch(e) {}
                }
            });
            
            // Strategy 4: Look for Review type in __INITIAL_STATE__
            const state = window.__INITIAL_STATE__;
            if (state) {
                for (const section of Object.keys(state)) {
                    const val = state[section];
                    if (val && typeof val === 'object') {
                        const str = JSON.stringify(val);
                        if (str.includes('"reviewText"') || str.includes('"review"') && str.includes('"rating"')) {
                            results.push({ method: 'redux-' + section, text: str.slice(0, 500) });
                        }
                    }
                }
            }
            
            return results;
        }''')
        
        print(f"  Found {len(all_reviews)} review data sources:")
        for r in all_reviews[:5]:
            print(f"    [{r['method']}] {r['text'][:300]}")
        
        # Deep scroll to trigger more review loading
        print("\n  Deep scrolling to trigger more reviews...")
        for i in range(8):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/8})')
            await asyncio.sleep(1)
        
        # Extract review cards again
        more_reviews = await page.evaluate('''() => {
            const results = [];
            const cards = document.querySelectorAll('[class*="review-card"], [class*="card"]');
            for (const card of cards) {
                const cls = (card.className || '');
                if (cls.includes('review') || card.textContent.includes('star')) {
                    const text = (card.textContent || '').replace(/\\s+/g, ' ').trim();
                    if (text.length > 100 && text.length < 5000) {
                        const cardClass = cls.slice(0, 60);
                        results.push({ class: cardClass, text: text.slice(0, 500) });
                        if (results.length >= 5) break;
                    }
                }
            }
            return results;
        }''')
        
        print(f"  Review cards after deep scroll: {len(more_reviews)}")
        for r in more_reviews[:3]:
            print(f"    [{r['class'][:50]}] {r['text'][:300]}")
        
        # Check what the "review-card" elements contain
        print("\n  Sample review-card inner HTML:")
        card_html = await page.evaluate('''() => {
            const cards = document.querySelectorAll('[class*="review-card"]');
            if (cards.length === 0) return 'NONE';
            return cards[0].outerHTML.slice(0, 2000);
        }''')
        print(f"  {card_html[:1500]}")
        
        await browser.close()

asyncio.run(probe())