"""
Comprehensive Review Scraper — Zola + TheKnot + WeddingWire
Scrapes review text, ratings, reviewer names, dates into DB.
Pilot: DJs, planners, photobooths in Indy + Chicago.
"""
import asyncio, json, os, re, sys, time
from pathlib import Path
from datetime import datetime, date

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/reviews')
OUT.mkdir(exist_ok=True, parents=True)

MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def parse_date(text):
    if not text: return None
    m = re.search(r'([A-Z][a-z]+)\s+(\d+),\s*(\d{4})', text)
    if m:
        try:
            month = MONTHS.index(m.group(1)) + 1
            return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
        except: pass
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def save_review(vendor_db_id, source, review_text, rating, reviewer_name, review_date, source_review_id):
    if not review_text or len(review_text) < 30:
        return None
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendor_reviews 
                (vendor_id, source, review_text, rating, review_date, reviewer_name, source_review_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_review_id) DO NOTHING
            RETURNING id
        """, (vendor_db_id, source, review_text[:3000], rating, review_date, reviewer_name[:100], source_review_id))
        rid = cur.fetchone()
        conn.commit()
        return rid[0] if rid else None
    except Exception as e:
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


def get_vendors(source, categories, limit=10):
    """Get vendors from DB by source and category"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(categories))
    cur.execute(f"""
        SELECT id, name, source_vendor_id, source_url, zola_slug, city, state
        FROM vendors 
        WHERE source = %s AND category IN ({placeholders})
        ORDER BY review_count DESC
        LIMIT %s
    """, [source] + categories + [limit])
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        'id': r[0], 'name': r[1], 'svid': r[2], 'url': r[3],
        'slug': r[4], 'city': r[5], 'state': r[6]
    } for r in rows]


# ─── ZOLA REVIEWS ──────────────────────────────────────────────

async def scrape_zola_reviews(vendor, page, browser):
    """Zola — scroll to trigger lazy-loaded reviews, extract from DOM"""
    slug = vendor.get('slug')
    name = vendor['name']
    vendor_url = f"https://www.zola.com/wedding-vendors/wedding-photographers/{slug}"
    
    try:
        await page.goto(vendor_url, wait_until='domcontentloaded', timeout=30000)
    except:
        await page.goto(vendor_url, wait_until='load', timeout=30000)
    await asyncio.sleep(4)
    
    # Deep scroll to trigger lazy review loading
    for i in range(12):
        await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/12})')
        await asyncio.sleep(1)
    
    # Try "Load more" buttons
    for _ in range(5):
        clicked = await page.evaluate('''() => {
            for (const b of document.querySelectorAll('button, [role="button"]')) {
                const t = (b.textContent || '').toLowerCase();
                if (t.includes('load more') || t.includes('more review') || t.includes('show more')) {
                    b.click(); return true;
                }
            }
            return false;
        }''')
        if not clicked: break
        await asyncio.sleep(2)
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
    
    # Extract all review-like text blocks
    reviews = await page.evaluate('''() => {
        const results = [];
        // Find the reviews section
        const reviewSection = document.querySelector('[class*="reviews-section"]');
        if (!reviewSection) return results;
        
        // Get all paragraphs with substantive text
        reviewSection.querySelectorAll('p, div[class*="review"], div[class*="testimonial"], div[class*="card"]').forEach(el => {
            const text = (el.textContent || '').trim();
            if (text.length > 50 && text.length < 5000) {
                results.push(text.replace(/\\s+/g, ' '));
            }
        });
        return results;
    }''')
    
    saved = 0
    for i, text_block in enumerate(reviews):
        # Try to parse reviewer name
        name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[A-Z]?\.?)', text_block)
        reviewer = name_match.group(1).strip().rstrip('.') if name_match else 'Anonymous'
        
        # Try to parse rating
        rating_match = re.search(r'Rating:\s*(\d+(?:\.\d+)?)', text_block)
        rating = float(rating_match.group(1)) if rating_match else None
        
        # Try to parse date
        rev_date = parse_date(text_block)
        
        # Clean the text (remove metadata prefix)
        clean = re.sub(r'^[A-Z].*?\.\s*Rating:\s*\d+(?:\.\d+)?.*?\d{4}', '', text_block, count=1)
        clean = re.sub(r'^\s*[•\s]+', '', clean)
        
        if len(clean) < 30:
            clean = text_block[:2000]
        
        rid = save_review(
            vendor['id'], 'zola', clean[:2000], rating, reviewer, rev_date,
            f"{vendor['svid']}-{i}"
        )
        if rid: saved += 1
    
    return saved


# ─── THEKNOT REVIEW SNIPPETS ─────────────────────────────────

async def scrape_theknot_reviews(vendor, page, browser):
    """TheKnot — extract review snippets from DOM + aggregate data"""
    url = vendor.get('url')
    if not url: return 0
    
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
    except:
        await page.goto(url, wait_until='load', timeout=30000)
    await asyncio.sleep(4)
    
    # Scroll to trigger review section
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight * 0.7)')
    await asyncio.sleep(2)
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await asyncio.sleep(2)
    
    # Extract review cards
    reviews = await page.evaluate('''() => {
        const results = [];
        const cards = document.querySelectorAll('[data-testid="review-snippets-card"]');
        cards.forEach((card, idx) => {
            const excerpt = card.querySelector('[data-testid="review-snippets-excerpt"]');
            const name = card.querySelector('[data-testid="review-snippets-reviewer-name"]');
            const rating = card.querySelector('[data-testid="review-snippets-card-rating"]');
            results.push({
                text: (excerpt ? excerpt.textContent : '').trim(),
                reviewer: (name ? name.textContent : '').trim(),
                rating: rating ? rating.textContent.trim() : ''
            });
        });
        return results;
    }''')
    
    saved = 0
    for i, r in enumerate(reviews):
        if len(r['text']) < 20: continue
        rating_val = None
        rm = re.search(r'(\d+(?:\.\d+)?)', r['rating'])
        if rm: rating_val = float(rm.group(1))
        
        rid = save_review(
            vendor['id'], 'theknot', r['text'][:2000], rating_val,
            r['reviewer'], None, f"{vendor['svid']}-snippet-{i}"
        )
        if rid: saved += 1
    
    return saved


async def scrape_all():
    from playwright.async_api import async_playwright
    
    categories = ['wedding-djs', 'wedding-planners', 'wedding-photographers']
    
    # Get vendors from DB
    zola_vendors = get_vendors('zola', categories, 10)
    tk_vendors = get_vendors('theknot', categories, 10)
    
    print(f"Zola vendors: {len(zola_vendors)}")
    print(f"TheKnot vendors: {len(tk_vendors)}")
    
    total_saved = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # Zola
        for v in zola_vendors:
            print(f"\n📷 Zola: {v['name']} ({v['city']}, {v['state']})")
            saved = await scrape_zola_reviews(v, page, browser)
            total_saved += saved
            print(f"  → {saved} reviews saved")
            await asyncio.sleep(2)
        
        # TheKnot
        for v in tk_vendors:
            print(f"\n📷 TheKnot: {v['name']} ({v['city']}, {v['state']})")
            saved = await scrape_theknot_reviews(v, page, browser)
            total_saved += saved
            print(f"  → {saved} review snippets saved")
            await asyncio.sleep(2)
        
        await browser.close()
    
    print(f"\n\nTotal reviews saved: {total_saved}")
    return total_saved


if __name__ == '__main__':
    asyncio.run(scrape_all())