"""
Debug why nationwide_reviews.py returned 0 — test single vendor directly
"""
import asyncio, json, os
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def debug():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Method 1: Navigate to vendor page first (like the WORKING scraper does)
        print("=== METHOD 1: Navigate to vendor page first ===")
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        storefront_id = await page.evaluate('() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""')
        print(f"  Storefront ID: {storefront_id}")
        
        query = ('reviews(input: { filters: { storefrontId: "%s" }, '
                'orderBy: { type: date, sort: desc }, '
                'pagination: { page: 1, size: 3 } }) { totalCount nodes { id comment { content } } }') % storefront_id
        
        result = await page.evaluate('''async function(qs) {
            try {
                const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify({query: "query { " + qs + " }"})
                });
                const d = await r.json();
                return JSON.stringify(d).slice(0, 500);
            } catch(e) { return JSON.stringify({fetch_error: e.message}); }
        }''', query)
        print(f"  Result: {result[:300]}")
        
        # Method 2: Just load /marketplace (like the FAILING script)
        print("\n=== METHOD 2: Only load /marketplace ===")
        page2 = await ctx.new_page()
        await page2.goto('https://www.theknot.com/marketplace',
                        wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        result2 = await page2.evaluate('''async function(qs) {
            try {
                const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                    body: JSON.stringify({query: "query { " + qs + " }"})
                });
                const d = await r.json();
                return JSON.stringify(d).slice(0, 500);
            } catch(e) { return JSON.stringify({fetch_error: e.message}); }
        }''', query)
        print(f"  Result: {result2[:300]}")
        
        # Method 3: Check current DB review count
        import psycopg2
        conn = psycopg2.connect(host='localhost', port=54329, user='postgres', password='devpass', dbname='wedding_vendors')
        cur = conn.cursor()
        
        cur.execute("SELECT source, COUNT(*) FROM vendor_reviews GROUP BY source")
        print("\n=== Current DB state ===")
        for r3 in cur.fetchall():
            print(f"  {r3[0]}: {r3[1]}")
        
        cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE source='theknot'")
        tk_count = cur.fetchone()[0]
        print(f"\nTheKnot total: {tk_count}")
        
        cur.execute("""
            SELECT v.name, v.review_count, COUNT(vr.id) as stored
            FROM vendors v LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id AND vr.source = 'theknot'
            WHERE v.source = 'theknot' AND v.review_count > 100
            GROUP BY v.name, v.review_count ORDER BY v.review_count DESC LIMIT 5
        """)
        print(f"\nTop vendors (DB review_count vs stored):")
        for r4 in cur.fetchall():
            print(f"  {r4[0][:35]:35s} | TK says: {r4[1]:5d} | We have: {r4[2]:5d}")
        
        cur.close(); conn.close()
        
        await browser.close()

asyncio.run(debug())