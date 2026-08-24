"""
Scale Zola reviews — scrape all 91 Zola vendors from DB
"""
import asyncio, json, os, re, sys
from pathlib import Path

os.environ.setdefault('DISPLAY', ':99')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

def parse_date(text):
    if not text: return None
    m = re.search(r'([A-Z][a-z]+)\s+(\d+),\s*(\d{4})', text)
    if m:
        try:
            month = MONTHS.index(m.group(1)) + 1
            return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
        except: pass
    return None

def save_review(vendor_db_id, source, review_text, rating, reviewer_name, review_date, source_review_id):
    if not review_text or len(review_text) < 30: return None
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendor_reviews (vendor_id, source, review_text, rating, review_date, reviewer_name, source_review_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_review_id) DO NOTHING
        """, (vendor_db_id, source, review_text[:3000], rating, review_date, reviewer_name[:100], source_review_id))
        conn.commit()
        return True
    except:
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def get_all_zola_vendors():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, zola_slug, category, city, state 
        FROM vendors WHERE source = 'zola' AND zola_slug != '' AND zola_slug IS NOT NULL
        ORDER BY category, city
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{'id': r[0], 'name': r[1], 'slug': r[2], 'category': r[3], 'city': r[4], 'state': r[5]} for r in rows]

async def main():
    from playwright.async_api import async_playwright
    
    vendors = get_all_zola_vendors()
    print(f"Total Zola vendors to scrape: {len(vendors)}")
    
    cat_counts = {}
    for v in vendors:
        cat = v['category'] or 'other'
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print(f"By category: {json.dumps(cat_counts)}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        total_saved = 0
        total_found = 0
        errors = 0
        
        for i, v in enumerate(vendors):
            slug = v['slug']
            url = f"https://www.zola.com/wedding-vendors/{v['category'] or 'wedding-photographers'}/{slug}"
            
            print(f"\n[{i+1}/{len(vendors)}] {v['name'][:40]:40s} | {v['category'] or '?':20s} | {v['city'] or '?':15s}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                # Deep scroll + load more
                for s in range(10):
                    await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(s+1)/10})')
                    await asyncio.sleep(0.8)
                
                for _ in range(4):
                    clicked = await page.evaluate("""() => {
                        for (const b of document.querySelectorAll('button'))
                            if ((b.textContent||'').toLowerCase().includes('load more')||(b.textContent||'').toLowerCase().includes('more review'))
                                { b.click(); return true; }
                        return false;
                    }""")
                    if not clicked: break
                    await asyncio.sleep(1.5)
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                
                # Extract review blocks
                blocks = await page.evaluate("""() => {
                    const sect = document.querySelector('[class*="reviews-section"]');
                    if (!sect) return [];
                    const results = [];
                    sect.querySelectorAll('p, div[class*="review"], div[class*="testimonial"]').forEach(el => {
                        const t = (el.textContent||'').trim();
                        if (t.length > 60 && t.length < 5000) results.push(t.replace(/\\s+/g,' '));
                    });
                    return results;
                }""")
                
                saved = 0
                seen_hashes = set()
                for bi, block in enumerate(blocks):
                    fprint = hash(block[:100])
                    if fprint in seen_hashes: continue
                    seen_hashes.add(fprint)
                    
                    name_m = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[A-Z]?\.?)', block)
                    reviewer = name_m.group(1).strip().rstrip('.') if name_m else 'Anonymous'
                    rating_m = re.search(r'Rating:\s*(\d+(?:\.\d+)?)', block)
                    rating = float(rating_m.group(1)) if rating_m else None
                    rev_date = parse_date(block)
                    
                    clean = re.sub(r'^[A-Z].*?\.\s*Rating:\s*\d+(?:\.\d+)?.*?\d{4}', '', block, count=1)
                    clean = re.sub(r'^\s*[•\s]+', '', clean)[:2000]
                    if len(clean) < 30: clean = block[:2000]
                    
                    ok = save_review(v['id'], 'zola', clean, rating, reviewer, rev_date, f"{v['id']}-{bi}")
                    if ok: saved += 1
                
                total_saved += saved
                total_found += len(blocks)
                print(f"  → {saved} saved / {len(blocks)} found")
                
            except Exception as e:
                errors += 1
                print(f"  ❌ Error: {str(e)[:80]}")
            
            await asyncio.sleep(1.5)
        
        await browser.close()
    
    print(f"\n\n{'='*60}")
    print(f"COMPLETE: {total_saved} reviews saved from {len(vendors)} vendors")
    print(f"Total blocks found: {total_found}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    asyncio.run(main())