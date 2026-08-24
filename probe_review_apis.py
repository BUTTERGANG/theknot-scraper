"""
Investigate TheKnot reviews GraphQL API + Zola/WeddingWire review DOM
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

async def probe():
    from playwright.async_api import async_playwright
    import random
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36')
        page = await ctx.new_page()
        
        # ========== THEKNOT ==========
        print("=" * 70)
        print("1. THEKNOT — GraphQL Review API")
        print("=" * 70)
        
        await page.goto(
            'https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
            wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Get vendor ID from state
        vendor_info = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            if (!s || !s.vendor) return null;
            const raw = s.vendor.vendorRaw || s.vendor.vendor || {};
            return {
                vendorId: raw.vendorId || '',
                displayId: raw.displayId || '',
                name: raw.name || '',
                accountId: raw.accountId || ''
            };
        }''')
        print(f"  Vendor: {vendor_info}")
        
        # Try GraphQL directly
        if vendor_info and vendor_info.get('vendorId'):
            print(f"\n  Probing GraphQL reviews API...")
            
            gql_result = await page.evaluate('''async (vendorId) => {
                const query = {
                    operationName: "GetVendorReviews",
                    variables: { vendorId: vendorId, first: 10, after: null },
                    query: `query GetVendorReviews($vendorId: ID!, $first: Int!, $after: String) {
                        vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                            edges { node { id rating title text createdAt } }
                            pageInfo { hasNextPage endCursor }
                        }
                    }`
                };
                try {
                    const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(query)
                    });
                    const data = await resp.json();
                    return JSON.stringify(data).substring(0, 3000);
                } catch(e) { return "FETCH_ERROR: " + e.message; }
            }''', vendor_info['vendorId'])
            
            print(f"  GraphQL response: {gql_result[:2000]}")
            
            # Also try different vendor ID (displayId)
            if vendor_info.get('displayId'):
                gql2 = await page.evaluate('''async (displayId) => {
                    const query = {
                        operationName: "GetVendorReviews",
                        variables: { vendorId: displayId, first: 10, after: null },
                        query: `query GetVendorReviews($vendorId: ID!, $first: Int!, $after: String) {
                            vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                                edges { node { id rating title text createdAt reviewer { name } } }
                                pageInfo { hasNextPage endCursor }
                            }
                        }`
                    };
                    try {
                        const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                            method: "POST", headers: {"Content-Type": "application/json"},
                            body: JSON.stringify(query)
                        });
                        const data = await resp.json();
                        return JSON.stringify(data).substring(0, 3000);
                    } catch(e) { return "ERROR: " + e.message; }
                }''', vendor_info['displayId'])
                print(f"  GraphQL (displayId): {gql2[:2000]}")
        
        # Check for reviews in the DOM after scrolling
        print(f"\n  DOM review content (after scrolling):")
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(3)
        
        dom_reviews = await page.evaluate('''() => {
            const results = [];
            const reviewEls = document.querySelectorAll('[class*="review"], [data-testid*="review"]');
            for (const el of reviewEls) {
                const text = (el.textContent || '').trim();
                if (text.length > 80 && text.length < 3000) {
                    results.push({
                        cls: (el.className || '').slice(0, 50),
                        text: text.replace(/\\s+/g, ' ').slice(0, 300)
                    });
                    if (results.length >= 3) break;
                }
            }
            return results;
        }''')
        print(f"  Found {len(dom_reviews)} review elements:")
        for r in dom_reviews:
            print(f"    [{r['cls'][:40]}] {r['text'][:200]}")
        
        # ========== ZOLA ==========
        print("\n" + "=" * 70)
        print("2. ZOLA — Review DOM Structure")
        print("=" * 70)
        
        await page.goto(
            'https://www.zola.com/wedding-vendors/wedding-photographers/the-talented-photographer-award-winning-photography',
            wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Scroll to trigger lazy-loaded reviews
        for i in range(3):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})')
            await asyncio.sleep(2)
        
        # Find review cards in DOM
        zola_reviews = await page.evaluate('''() => {
            const results = [];
            // Zola review cards are typically in sections
            const allElements = document.querySelectorAll('p, blockquote, [class*="review"], [class*="card"]');
            for (const el of allElements) {
                const text = (el.textContent || '').trim();
                if (text.length > 120 && text.length < 3000) {
                    if (!text.includes('cookie') && !text.includes('privacy') && !text.includes('Zola')) {
                        results.push({
                            tag: el.tagName,
                            cls: (el.className || '').slice(0, 50),
                            text: text.replace(/\\s+/g, ' ').slice(0, 300)
                        });
                        if (results.length >= 5) break;
                    }
                }
            }
            return results;
        }''')
        print(f"  Zola review-length elements: {len(zola_reviews)}")
        for r in zola_reviews[:3]:
            print(f"    [{r['tag']}] [{r['cls'][:40]}] {r['text'][:200]}")
        
        # Check __NEXT_DATA__ for review arrays
        nd_reviews = await page.evaluate('''() => {
            const nd = document.getElementById("__NEXT_DATA__");
            if (!nd) return null;
            try {
                const data = JSON.parse(nd.textContent);
                const sf = data?.props?.pageProps?.storefront || {};
                const reviews = {};
                for (const k of Object.keys(sf)) {
                    if (k.toLowerCase().includes('review') || k === 'testimonials' || k === 'featuredReviews') {
                        const v = sf[k];
                        reviews[k] = typeof v === 'object' ? JSON.stringify(v).slice(0, 500) : v;
                    }
                }
                return reviews;
            } catch(e) { return {error: e.message}; }
        }''')
        print(f"\n  __NEXT_DATA__ review fields: {json.dumps(nd_reviews, default=str)[:1500]}")
        
        # ========== WEDDINGWIRE ==========
        print("\n" + "=" * 70)
        print("3. WEDDINGWIRE — Review DOM Structure")
        print("=" * 70)
        
        await page.goto(
            'https://www.weddingwire.com/biz/southern-palms-studio-saint-augustine/51ec19bd45b74c48.html',
            wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Scroll and click "load more" / review links
        for i in range(3):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})')
            await asyncio.sleep(2)
        
        # Try clicking "Reviews" tab or "See all reviews"
        await page.evaluate('''() => {
            const links = document.querySelectorAll('a, button, [role="tab"]');
            for (const el of links) {
                const t = (el.textContent || '').toLowerCase().trim();
                if (t === 'reviews' || t.includes('reviews') || t.includes('read all')) {
                    el.click();
                    break;
                }
            }
        }''')
        await asyncio.sleep(3)
        
        ww_reviews = await page.evaluate('''() => {
            const results = {};
            
            // Look for review elements
            const reviewItems = document.querySelectorAll('[class*="review"], [class*="feedback"], [class*="review-item"]');
            results.reviewElements = reviewItems.length;
            
            if (reviewItems.length > 0) {
                results.sample = reviewItems[0].textContent.replace(/\\s+/g, ' ').slice(0, 400);
                results.sampleClass = (reviewItems[0].className || '').slice(0, 60);
            }
            
            // Check JSON-LD for review data
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d["@type"] === "LocalBusiness" && d.review) {
                        results.jsonldReviewCount = Array.isArray(d.review) ? d.review.length : 1;
                        results.jsonldSample = JSON.stringify(Array.isArray(d.review) ? d.review[0] : d.review).slice(0, 500);
                    }
                } catch(e) {}
            }
            
            return results;
        }''')
        print(f"  WeddingWire reviews: {json.dumps(ww_reviews, default=str)[:1500]}")
        
        await browser.close()

asyncio.run(probe())