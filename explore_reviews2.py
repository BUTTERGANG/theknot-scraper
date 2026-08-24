"""
Deep investigation into actual review data available in page states
"""
import json, os, asyncio
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

# Check if the big vendor detail state file still exists
vd_file = out / 'vendor_detail_state.json'
if vd_file.exists():
    with open(vd_file) as f:
        detail = json.load(f)
    
    print("=== VENDOR DETAIL STATE REVIEW DATA ===\n")
    
    def deep_find(obj, path="", depth=0):
        if depth > 6: return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(x in k.lower() for x in ['review', 'comment', 'feedback', 'testimonial', 'praise']):
                    if isinstance(v, (list, dict)):
                        s = json.dumps(v, default=str)
                        print(f"  {path}.{k} = {type(v).__name__} ({len(s)} chars)")
                        if isinstance(v, list) and len(v) > 0:
                            item = v[0]
                            if isinstance(item, dict):
                                print(f"    [0] keys: {list(item.keys())[:15]}")
                                # Show text field
                                for tk in ['reviewText', 'text', 'review', 'comment', 'description', 'body']:
                                    if tk in item:
                                        print(f"    [0].{tk}: {str(item[tk])[:300]}")
                            else:
                                print(f"    [0]: {str(item)[:300]}")
                deep_find(v, f"{path}.{k}", depth + 1)
        elif isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
            deep_find(obj[0], f"{path}[0]", depth + 1)
    
    vendor_section = detail.get('vendor', {})
    deep_find(vendor_section)
else:
    print("vendor_detail_state.json not found")

# Now let's scrape a fresh TheKnot vendor page and see the FULL initial state
print("\n\n=== SCRAPING FRESH THEKNOT VENDOR PAGE FOR REVIEW ANALYSIS ===\n")

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def check_vendor_reviews():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        # TheKnot vendor page
        url = "https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253"
        print(f"Loading: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        state = await page.evaluate('() => window.__INITIAL_STATE__')
        if state:
            v = state.get('vendor', {})
            print(f"\n--- State sections ---")
            print(f"  vendor keys: {list(v.keys()) if isinstance(v, dict) else type(v).__name__}")
            
            raw = v.get('vendorRaw', {})
            obj = v.get('vendor', {})
            
            # Show review-related fields in raw
            print(f"\n--- vendorRaw review fields ---")
            for k in sorted(raw.keys()):
                if 'review' in k.lower():
                    s = json.dumps(raw[k], default=str)
                    print(f"  {k}: {s[:400]}")
            
            # Check if reviews are in a separate state section
            print(f"\n--- Top-level state review sections ---")
            for k in sorted(state.keys()):
                if 'review' in k.lower() or 'vrm' in k.lower():
                    s = json.dumps(state[k], default=str)
                    print(f"  {k}: {s[:300]}")
            
            # Check 'vrm' (vendor review management?) section
            vrm = state.get('vrm', {})
            if vrm:
                print(f"\n--- VRM section ---")
                print(f"  keys: {list(vrm.keys())[:15]}")
                for k in vrm:
                    v = vrm[k]
                    s = json.dumps(v, default=str)
                    if 'review' in k.lower() or isinstance(v, list):
                        print(f"  {k} ({type(v).__name__}): {s[:500]}")
            
            # Check for any list of reviews in the page HTML
            print(f"\n--- Looking for review elements in DOM ---")
            review_count = await page.evaluate('''() => {
                const els = document.querySelectorAll('[class*="review"], [data-testid*="review"], [class*="Review"]');
                return els.length;
            }''')
            print(f"  Elements with 'review' in class/data-testid: {review_count}")
            
            # Check what the visible review section says
            review_area = await page.evaluate('''() => {
                const sections = document.querySelectorAll('section, div[class*="section"]');
                for (const s of sections) {
                    const text = s.textContent.toLowerCase();
                    if (text.includes('review') && (text.includes('star') || text.includes('rating'))) {
                        return {tag: s.tagName, class: (s.className || '').substring(0, 80), text: s.textContent.substring(0, 500).replace(/\\s+/g, ' ')};
                    }
                }
                return null;
            }''')
            if review_area:
                print(f"  Review section found:")
                print(f"    class: {review_area.get('class', '')}")
                print(f"    text: {review_area.get('text', '')[:500]}")
            else:
                print(f"  No explicit review section found in DOM")
            
            # Check for vendor-reviews endpoint
            print(f"\n--- Checking API for reviews ---")
            # TheKnot likely loads reviews via XHR - check for API calls
            api_pattern = await page.evaluate('''() => {
                const scripts = document.querySelectorAll('script');
                for (const s of scripts) {
                    const text = s.textContent || '';
                    if (text.includes('review') && (text.includes('/api/') || text.includes('graphql') || text.includes('vendor-rating'))) {
                        const lines = text.split('\\n').filter(l => l.includes('review') && (l.includes('/api/') || l.includes('graphql')));
                        return lines.slice(0, 3).join('\\n').substring(0, 500);
                    }
                }
                return null;
            }''')
            if api_pattern:
                print(f"  Found API pattern: {api_pattern}")
            
            # Check for Redux store shape more broadly
            print(f"\n--- All top-level Redux state keys ---")
            for k in sorted(state.keys()):
                v = state[k]
                if isinstance(v, dict):
                    print(f"  {k}: dict ({len(v)} keys)")
                elif isinstance(v, list):
                    print(f"  {k}: list[{len(v)}]")
                else:
                    print(f"  {k}: {type(v).__name__}")
            
            # Save full state for offline analysis
            with open(out / 'vendor_review_state.json', 'w') as f:
                json.dump(state, f, indent=2, default=str)
            print(f"\nFull state saved to vendor_review_state.json")
        
        # Also check Zola for review data
        print(f"\n\n=== ZOLA VENDOR REVIEW DATA ===\n")
        await page.goto('https://www.zola.com/wedding-vendors/wedding-photographers/the-talented-photographer-award-winning-photography',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        nd = await page.evaluate('''() => {
            const el = document.getElementById("__NEXT_DATA__");
            return el ? JSON.parse(el.textContent) : null;
        }''')
        
        if nd:
            sf = nd.get('props', {}).get('pageProps', {}).get('storefront', {})
            print(f"Storefront keys with 'review':")
            for k in sf:
                if 'review' in k.lower():
                    print(f"  {k}: {json.dumps(sf[k], default=str)[:300]}")
            
            with open(out / 'zola_review_state.json', 'w') as f:
                json.dump(nd, f, indent=2, default=str)
            print(f"Zola state saved")
        
        # Also check WeddingWire biz page for review data
        print(f"\n\n=== WEDDINGWIRE REVIEW DATA ===\n")
        await page.goto('https://www.weddingwire.com/biz/southern-palms-studio-saint-augustine/51ec19bd45b74c48.html',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        # Check for Embedded Data / Apollo / Hypernova
        apollo = await page.evaluate('() => typeof window.__APOLLO_STATE__ !== "undefined" ? Object.keys(window.__APOLLO_STATE__).length : null')
        init = await page.evaluate('() => typeof window.__INITIAL_STATE__ !== "undefined" ? "YES" : null')
        print(f"  __APOLLO_STATE__: {apollo} keys" if apollo else "  __APOLLO_STATE__: NOT FOUND")
        print(f"  __INITIAL_STATE__: {init}" if init else "  __INITIAL_STATE__: NOT FOUND")
        
        # Check for review data in page
        ww_reviews = await page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d["@type"] === "LocalBusiness" && d.review) {
                        return JSON.stringify(d.review).substring(0, 1000);
                    }
                } catch(e) {}
            }
            return null;
        }''')
        print(f"  JSON-LD reviews: {ww_reviews[:500] if ww_reviews else 'NONE'}")
        
        # Check for review elements on WeddingWire
        ww_review_els = await page.evaluate('''() => {
            const reviews = document.querySelectorAll('[class*="review"], [data-testid*="review"]');
            if (reviews.length > 0) {
                return Array.from(reviews).slice(0, 2).map(r => ({
                    class: (r.className || '').substring(0, 80),
                    text: r.textContent.substring(0, 200).replace(/\\s+/g, ' ')
                }));
            }
            // Try finding rating elements
            const ratings = document.querySelectorAll('[class*="rating"], [class*="Rating"]');
            return Array.from(ratings).slice(0, 3).map(r => ({
                class: (r.className || '').substring(0, 60),
                text: r.textContent.substring(0, 200).replace(/\\s+/g, ' ')
            }));
        }''')
        print(f"  Review/rating elements: {json.dumps(ww_review_els, default=str)[:600] if ww_review_els else 'NONE'}")
        
        await browser.close()

asyncio.run(check_vendor_reviews())