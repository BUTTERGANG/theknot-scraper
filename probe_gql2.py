"""
Final probe — correct GraphQL header + find full review pages
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
        
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        vendor_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.vendorId || ""')
        display_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.displayId || ""')
        print(f"Vendor: {vendor_id} / Display: {display_id}")
        
        # Try GraphQL with tk-us
        print("\n=== GraphQL with x-tenant-id: tk-us ===")
        gql = await page.evaluate('''async (vid) => {
            const q = {
                operationName: "GetVendorReviews",
                variables: { vendorId: vid, first: 20, after: null },
                query: `query Q($vendorId: ID!, $first: Int!, $after: String) {
                    vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                        edges { node { id rating title text createdAt reviewer { name } } }
                        pageInfo { hasNextPage endCursor totalCount }
                    }
                }`
            };
            const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                method:"POST", 
                headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                body: JSON.stringify(q)
            });
            const d = await r.json();
            const edges = d?.data?.vendorReviews?.edges || [];
            const pi = d?.data?.vendorReviews?.pageInfo || {};
            return edges.length + " reviews. hasNext=" + pi.hasNextPage + " total=" + pi.totalCount;
        }''', vendor_id)
        print(f"  Result: {gql}")
        
        # Get full data
        print("\n=== Full GraphQL response ===")
        full = await page.evaluate('''async (vid) => {
            const q = {
                operationName: "GetVendorReviews",
                variables: { vendorId: vid, first: 10, after: null },
                query: `query Q($vendorId: ID!, $first: Int!, $after: String) {
                    vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                        edges { node { id rating title text createdAt reviewer { name location } } }
                        pageInfo { hasNextPage endCursor totalCount }
                    }
                }`
            };
            const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                method:"POST",
                headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                body: JSON.stringify(q)
            });
            const d = await r.json();
            return JSON.stringify(d, null, 2).slice(0, 5000);
        }''', vendor_id)
        print(full[:4000])
        
        # Paginate: get all reviews
        print("\n=== Paginating through all reviews ===")
        all_reviews = await page.evaluate('''async (vid) => {
            const results = [];
            let after = null;
            let hasMore = true;
            let page = 0;
            
            while (hasMore && page < 5) {
                const q = {
                    operationName: "GetVendorReviews",
                    variables: { vendorId: vid, first: 50, after: after },
                    query: `query Q($vendorId: ID!, $first: Int!, $after: String) {
                        vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                            edges { node { id rating title text createdAt } }
                            pageInfo { hasNextPage endCursor totalCount }
                        }
                    }`
                };
                const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method:"POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify(q)
                });
                const d = await r.json();
                const data = d?.data?.vendorReviews;
                if (!data) break;
                
                for (const edge of data.edges) {
                    results.push(edge.node);
                }
                
                hasMore = data.pageInfo?.hasNextPage;
                after = data.pageInfo?.endCursor;
                page++;
            }
            return { total: results.length, pageInfo: { pages: page }, samples: results.slice(0, 3) };
        }''', vendor_id)
        print(json.dumps(all_reviews, default=str)[:2000])
        
        # Now find the review count endpoint to understand total
        total_count = await page.evaluate('''async (vid) => {
            const q = {
                operationName: "GetVendorReviews",
                variables: { vendorId: vid, first: 1, after: null },
                query: `query Q($vendorId: ID!, $first: Int!, $after: String) {
                    vendorReviews(vendorId: $vendorId, first: $first, after: $after) {
                        pageInfo { totalCount }
                    }
                }`
            };
            const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                method:"POST",
                headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                body: JSON.stringify(q)
            });
            const d = await r.json();
            return d?.data?.vendorReviews?.pageInfo?.totalCount || 0;
        }''', vendor_id)
        print(f"\nTotal reviews for this vendor: {total_count}")
        
        # ========== ZOLA REVIEWS ==========
        print("\n\n=== ZOLA — Find review API ===")
        await page.goto('https://www.zola.com/wedding-vendors/wedding-photographers/the-talented-photographer-award-winning-photography',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        # Scroll to load reviews
        for i in range(5):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/5})')
            await asyncio.sleep(1.5)
        
        # Find review text
        review_texts = await page.evaluate('''() => {
            const results = [];
            // Look for review-specific elements
            const selectors = ['[class*="review"]', '[class*="testimonial"]', '[class*="feedback"]'];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const t = (el.textContent || '').trim();
                    if (t.length > 150 && t.length < 5000) {
                        results.push({
                            sel: sel,
                            cls: (el.className || '').slice(0, 50),
                            text: t.replace(/\\s+/g, ' ').slice(0, 300)
                        });
                        if (results.length >= 5) break;
                    }
                }
                if (results.length >= 5) break;
            }
            return results;
        }''')
        print(f"  Review elements: {len(review_texts)}")
        for r in review_texts[:3]:
            print(f"    [{r['sel']}] [{r['cls'][:40]}] {r['text'][:200]}")
        
        # Check for a "reviews" API endpoint in page source
        api_patterns = await page.evaluate('''() => {
            const html = document.documentElement.outerHTML;
            const patterns = [];
            const matches = html.match(/api\\.zola\\.com[^"']*/g);
            if (matches) patterns.push(...matches.slice(0, 5));
            const gqlMatches = html.match(/gql|graphql[^"']*/g);
            if (gqlMatches) patterns.push(...gqlMatches.slice(0, 5));
            return patterns;
        }''')
        print(f"  API patterns in source: {api_patterns}")
        
        await browser.close()

asyncio.run(probe())