"""
Zola Review Scraper — extract full review text from vendor detail pages

Reviews are rendered in the DOM after scrolling. Each review contains:
- Reviewer name, rating, date, source ("Zola")
- Full review text
- Pagination via "Load more" button or scroll
"""
import asyncio, json, os, re, sys
from pathlib import Path
from datetime import datetime, date

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import db_writer
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/reviews')
OUT.mkdir(exist_ok=True, parents=True)

PARSE_DATE = re.compile(r'([A-Z][a-z]+)\s+(\d+),\s*(\d{4})')
PARSE_DATE2 = re.compile(r'(\d{4})-(\d{2})-(\d{2})')


def parse_date(text):
    """Parse dates like 'Jul 13, 2026' or '2026-07-13'"""
    m = PARSE_DATE.search(text or '')
    if m:
        months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
        try:
            month = months.index(m.group(1)) + 1
            return date(int(m.group(3)), month, int(m.group(2)))
        except:
            pass
    m2 = PARSE_DATE2.search(text or '')
    if m2:
        return date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    return None


def save_review(vendor_name, vendor_db_id, source, review_text, rating, reviewer_name, review_date, source_review_id, source_vendor_id):
    """Save a review to the database"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendor_reviews 
                (vendor_id, source, review_text, rating, review_date, reviewer_name, 
                 source_review_id, source_vendor_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_review_id) DO UPDATE SET
                review_text = EXCLUDED.review_text,
                rating = EXCLUDED.rating,
                review_date = EXCLUDED.review_date,
                reviewer_name = EXCLUDED.reviewer_name
            RETURNING id
        """, (vendor_db_id, source, review_text, rating, review_date, reviewer_name,
              source_review_id, source_vendor_id))
        rid = cur.fetchone()[0]
        conn.commit()
        return rid
    except Exception as e:
        print(f"    DB error: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


async def scrape_zola_reviews(vendor_name, vendor_url, vendor_db_id, source_vendor_id):
    """Scrape all reviews from a Zola vendor detail page"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        print(f"\n📷 Zola reviews: {vendor_name}")
        print(f"  URL: {vendor_url}")
        
        await page.goto(vendor_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        # Scroll to load reviews section
        for i in range(8):
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/8})')
            await asyncio.sleep(1.5)
        
        # Try clicking "Load more" buttons
        for attempt in range(5):
            clicked = await page.evaluate('''() => {
                const btns = document.querySelectorAll('button, a, [role="button"]');
                for (const btn of btns) {
                    const t = (btn.textContent || '').toLowerCase();
                    if (t.includes('load more') || t.includes('show more') || t.includes('see more')) {
                        btn.click();
                        return btn.textContent.trim();
                    }
                }
                return null;
            }''')
            if not clicked:
                break
            await asyncio.sleep(2)
            # Scroll after load
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
        
        # Extract all reviews from DOM
        reviews = await page.evaluate('''() => {
            const results = [];
            
            // Find all review sections
            const reviewSections = document.querySelectorAll('[class*="reviews-section"], [class*="reviewsContent"], [class*="review-section"]');
            
            if (reviewSections.length > 0) {
                for (const section of reviewSections) {
                    const items = section.querySelectorAll('[class*="review"], [class*="testimonial"], [class*="feedback"]');
                    for (const item of items) {
                        const text = (item.textContent || '').trim();
                        if (text.length > 50) {
                            results.push({
                                cls: (item.className || '').slice(0, 60),
                                text: text.replace(/\\s+/g, ' ').slice(0, 3000)
                            });
                        }
                    }
                }
            }
            
            // Fallback: find review-like content in the page
            if (results.length === 0) {
                // Zola stores reviews in a specific class pattern
                const allDivs = document.querySelectorAll('div[class*="review"], div[class*="Review"]');
                for (const div of allDivs) {
                    const text = (div.textContent || '').trim();
                    // Check if it looks like a review (has rating + readable text)
                    if (text.length > 100 && text.length < 3000) {
                        if (!text.includes('cookie') && !text.includes('privacy')) {
                            results.push({
                                cls: (div.className || '').slice(0, 60),
                                text: text.replace(/\\s+/g, ' ').slice(0, 3000)
                            });
                        }
                    }
                }
            }
            
            return results;
        }''')
        
        print(f"  Found {len(reviews)} review elements")
        
        # Parse individual reviews from the DOM blocks
        # Zola reviews are in a stacked format like:
        # "Reviewer N.Rating: 5•Zola•Jul 13, 2026Full review text here..."
        parsed = []
        seen_texts = set()
        
        for r in reviews:
            text = r['text']
            
            # Try to split by reviewer pattern: "Name.Rating: X•Source•Date"
            parts = re.split(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[A-Z]?\.?\s*Rating:\s*\d+)', text)
            
            if len(parts) > 1:
                # Structured review blocks
                for i in range(1, len(parts), 2):
                    header = parts[i]
                    body = parts[i+1] if i+1 < len(parts) else ''
                    
                    # Parse reviewer name
                    name_match = re.match(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[A-Z]?\.?)', header)
                    reviewer = name_match.group(1).strip().rstrip('.') if name_match else ''
                    
                    # Parse rating
                    rating_match = re.search(r'Rating:\s*(\d+(?:\.\d+)?)', header)
                    rating = float(rating_match.group(1)) if rating_match else None
                    
                    # Parse date
                    date_match = re.search(r'([A-Z][a-z]+)\s+(\d+),\s*(\d{4})', text[max(0, text.index(header)-200):text.index(header)+200])
                    review_date = None
                    if date_match:
                        months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
                        month = months.index(date_match.group(1)) + 1
                        review_date = f"{date_match.group(3)}-{month:02d}-{int(date_match.group(2)):02d}"
                    
                    # Clean body text
                    body = body.strip().rstrip('•')
                    
                    # Dedup
                    dedup_key = (reviewer, body[:100])
                    if dedup_key not in seen_texts and len(body) > 30:
                        seen_texts.add(dedup_key)
                        parsed.append({
                            'reviewer': reviewer,
                            'rating': rating,
                            'date': review_date,
                            'text': body[:2000],
                        })
            else:
                # Unstructured — try direct extraction
                body = text
                # Check if it looks like a single review
                if len(body) > 80 and len(body) < 3000:
                    # Try to extract rating
                    rating_match = re.search(r'Rating:\s*(\d+(?:\.\d+)?)', body)
                    rating = float(rating_match.group(1)) if rating_match else None
                    
                    # Try to extract reviewer
                    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[A-Z]?\.?)', body)
                    reviewer = name_match.group(1).strip().rstrip('.') if name_match else ''
                    
                    dedup_key = (reviewer, body[:100])
                    if dedup_key not in seen_texts and len(body) > 50:
                        seen_texts.add(dedup_key)
                        parsed.append({
                            'reviewer': reviewer or 'Anonymous',
                            'rating': rating,
                            'date': None,
                            'text': body[:2000],
                        })
        
        print(f"  Parsed {len(parsed)} individual reviews")
        
        # Save to DB
        saved = 0
        for i, rev in enumerate(parsed):
            rid = save_review(
                vendor_name=vendor_name,
                vendor_db_id=vendor_db_id,
                source='zola',
                review_text=rev['text'],
                rating=rev['rating'],
                reviewer_name=rev['reviewer'],
                review_date=rev['date'],
                source_review_id=f"{source_vendor_id}-{i}",
                source_vendor_id=source_vendor_id,
            )
            if rid:
                saved += 1
        
        print(f"  Saved to DB: {saved}/{len(parsed)}")
        
        # Show samples
        if parsed:
            for r in parsed[:3]:
                print(f"    [{r['rating']}★] {r['reviewer']} ({r['date'] or '?'})")
                print(f"      {r['text'][:200]}...")
        
        await browser.close()
        return parsed


async def main():
    print("=" * 60)
    print("ZOLA REVIEW SCRAPER — PILOT")
    print("=" * 60)
    
    # Get Zola vendors from DB that have slugs
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, zola_slug FROM vendors 
        WHERE source = 'zola' AND zola_slug != '' AND zola_slug IS NOT NULL
        LIMIT 5
    """)
    vendors = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"Found {len(vendors)} Zola vendors with slugs to scrape\n")
    
    for vendor_id, name, slug in vendors:
        vendor_url = f"https://www.zola.com/wedding-vendors/wedding-photographers/{slug}"
        reviews = await scrape_zola_reviews(name, vendor_url, vendor_id, slug)
        print(f"  → {len(reviews)} reviews for {name}")
        # Brief pause between vendors
        await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main())