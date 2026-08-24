"""
TheKnot Review Scraper v2 — WORKING GraphQL query
Pulls ALL reviews with full text, ratings, reviewer info.

Query structure:
  reviews(input: { filters: { storefrontId }, orderBy: { type, sort }, pagination: { page, size } }) {
    totalCount
    pageInfo { hasNextPage }
    nodes {
      id createdAt title
      comment { content }
      ratings { value name }
      reviewer { id firstName lastName email }
    }
  }
"""
import asyncio, json, os, sys, time, re
from pathlib import Path
from datetime import datetime

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/reviews')


def save_review(vendor_db_id, source, review_text, rating, reviewer_name, review_date, source_review_id):
    if not review_text or len(review_text) < 10:
        return None
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendor_reviews (vendor_id, source, review_text, rating, review_date, reviewer_name, source_review_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_review_id) DO UPDATE SET
                review_text = EXCLUDED.review_text,
                rating = EXCLUDED.rating,
                review_date = EXCLUDED.review_date,
                reviewer_name = EXCLUDED.reviewer_name
        """, (vendor_db_id, source, review_text[:5000], rating, review_date, reviewer_name[:200], source_review_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


async def scrape_theknot_reviews(storefront_id, page):
    """Scrape ALL reviews from a TheKnot vendor via GraphQL API."""
    
    all_reviews = []
    total_count = 0
    page_size = 50
    
    for page_num in range(1, 100):  # Max ~5000 reviews per vendor
        try:
            q = ('reviews(input: { filters: { storefrontId: "%s" }, '
                 'orderBy: { type: date, sort: desc }, '
                 'pagination: { page: %d, size: %d } }) { '
                 'totalCount pageInfo { hasNextPage } '
                 'nodes { id createdAt title comment { content } '
                 'ratings { value name } '
                 'reviewer { firstName lastName email } } }'
            ) % (storefront_id, page_num, page_size)
            
            result = await page.evaluate('''async function(queryStr) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type":"application/json", "x-tenant-id":"tk-us"},
                        body: JSON.stringify({query: "query { " + queryStr + " }"})
                    });
                    const d = await r.json();
                    if (d.data) return {ok: true, data: JSON.stringify(d.data)};
                    const msgs = d.errors ? d.errors.map(function(e) {return e.message;}).join("; ") : "no data";
                    return {ok: false, error: msgs};
                } catch(e) { return {ok: false, error: e.message}; }
            }''', q)
            
            if not result.get('ok'):
                print(f"    Page {page_num} API error: {result.get('error', '')[:100]}")
                break
            
            data = json.loads(result['data']).get('reviews', {})
            
            if page_num == 1:
                total_count = data.get('totalCount', 0)
                print(f"    Total reviews on TheKnot: {total_count}")
            
            nodes = data.get('nodes', [])
            if not nodes:
                break
            
            # Parse reviews into our format
            for node in nodes:
                review_text = (node.get('comment') or {}).get('content', '')
                created_at = node.get('createdAt', '')
                
                # Calculate average rating from the category breakdown
                ratings_list = node.get('ratings', []) or []
                values = [r.get('value', 0) for r in ratings_list if r.get('value')]
                avg_rating = sum(values) / len(values) if values else None
                
                reviewer = node.get('reviewer') or {}
                first = reviewer.get('firstName', '')
                last = reviewer.get('lastName', '')
                reviewer_name = f"{first} {last}".strip()
                
                # Parse date
                date_str = ''
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                    except: pass
                
                all_reviews.append({
                    'id': node.get('id'),
                    'text': review_text[:5000],
                    'rating': round(avg_rating, 1) if avg_rating else None,
                    'category_ratings': {r['name']: r['value'] for r in ratings_list},
                    'reviewer': reviewer_name,
                    'email': reviewer.get('email', ''),
                    'date': date_str,
                    'created_at': created_at,
                })
            
            has_next = data.get('pageInfo', {}).get('hasNextPage', False)
            
            if not has_next or len(all_reviews) >= total_count:
                break
            
            await asyncio.sleep(0.5)  # Rate limit
            
        except Exception as e:
            print(f"    Page {page_num} exception: {e}")
            break
    
    return all_reviews, total_count


async def main():
    """Scrape reviews for TheKnot vendors in our DB"""
    from playwright.async_api import async_playwright
    
    # Get TheKnot vendors that have URLs in DB
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, source_vendor_id, source_url 
        FROM vendors 
        WHERE source = 'theknot' AND source_url != '' AND source_url IS NOT NULL
        ORDER BY review_count DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    print(f"TheKnot vendors to scrape: {len(rows)}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        total_saved = 0
        
        for db_id, name, svid, url in rows:
            print(f"\n📷 TheKnot: {name}")
            print(f"   URL: {url}")
            
            # Navigate to get cookies/session + extract storefront ID
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"  Navigation error: {e}")
                continue
            
            storefront_id = await page.evaluate(
                '() => window.__INITIAL_STATE__?.vendor?.vendorRaw?.id || ""'
            )
            
            if not storefront_id:
                print(f"  ⚠️ No storefront ID found, skipping")
                continue
            
            print(f"   Storefront ID: {storefront_id}")
            
            # Scrape all reviews via GraphQL
            reviews, tk_total = await scrape_theknot_reviews(storefront_id, page)
            
            print(f"   Fetched: {len(reviews)}/{tk_total} reviews")
            
            # Save to DB
            saved = 0
            for rev in reviews:
                ok = save_review(
                    vendor_db_id=db_id,
                    source='theknot',
                    review_text=rev['text'],
                    rating=rev['rating'],
                    reviewer_name=rev['reviewer'],
                    review_date=rev['date'],
                    source_review_id=rev['id'],
                )
                if ok: saved += 1
            
            total_saved += saved
            print(f"   Saved to DB: {saved}/{len(reviews)}")
            
            # Show sample
            if reviews:
                sample = reviews[0]
                print(f"   Sample [{sample['rating']}★] {sample['reviewer']}: {sample['text'][:100]}...")
            
            # Brief pause between vendors
            await asyncio.sleep(2)
        
        await browser.close()
    
    print(f"\n{'='*60}")
    print(f"TOTAL REVIEWS SAVED: {total_saved}")

if __name__ == '__main__':
    asyncio.run(main())