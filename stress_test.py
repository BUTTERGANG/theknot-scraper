"""
STRESS TEST — push scrapers to see where they break
Tests rate limiting, bot detection, CAPTCHAs at scale.

Runs: TheKnot (15 vendors), Zola (pagination), WeddingWire
Logs: every request status, timing, errors
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/stress')
OUT.mkdir(exist_ok=True, parents=True)

@dataclass
class RequestLog:
    source: str
    url: str
    status: str  # ok, blocked, captcha, error
    html_size: int = 0
    elapsed: float = 0.0
    title: str = ''
    error: str = ''
    blocks_detected: list = field(default_factory=list)

async def check_page(page) -> tuple:
    """Check if page is blocked. Returns (status, [block_keywords])"""
    body_text = ''
    try:
        body_text = await page.inner_text('body')
    except:
        pass
    
    title = ''
    try:
        title = await page.title()
    except:
        pass
    
    content = ''
    try:
        content = await page.content()
    except:
        pass
    
    blocks = []
    for kw in ['403 forbidden', 'access denied', 'you have been blocked', 'your access has been blocked',
              'unusual traffic', 'automated requests', 'bot detected', 'captcha required',
              'please verify you are a human', 'enable javascript and cookies',
              'perimeterx', 'px-captcha', 'challenge']:
        if kw in body_text.lower() or kw in content.lower():
            blocks.append(kw)
    
    if blocks:
        return ('blocked', blocks)
    
    # Check CAPTCHA
    captcha_indicators = ['g-recaptcha', 'h-captcha', 'px-captcha', 'cf-challenge']
    for ci in captcha_indicators:
        if ci in content.lower():
            return ('captcha', [ci])
    
    if len(content or '') < 1000:
        return ('error', ['empty_content'])
    
    return ('ok', [])


async def stress_theknot(results):
    """Test TheKnot at increasing intensity"""
    sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
    from theknot_scraper_v2 import TheKnotScraperV2
    
    print("\n" + "=" * 60)
    print("STRESS TEST: THEKNOT (15 vendors)")
    print("=" * 60)
    
    tk = TheKnotScraperV2(output_dir=str(OUT))
    await tk.start()
    
    try:
        # Get search results page
        print("[1] Fetching search page...")
        url = "https://www.theknot.com/marketplace/wedding-photographers-indianapolis-in"
        await tk._goto(url, wait_after=5)
        status, blocks = await check_page(tk.page)
        content = await tk.page.content()
        results.append(RequestLog(
            source='theknot', url=url, status=status,
            html_size=len(content), title=await tk.page.title(),
            blocks_detected=blocks
        ))
        print(f"  Search: {status} ({len(content):,} chars) blocks={blocks}")
        
        if status != 'ok':
            print("  ❌ Search page blocked! Aborting detail scrapes.")
            return
        
        # Extract vendor URLs from search state
        state = await tk._extract_initial_state()
        vendors = []
        if state and 'search' in state:
            for v in (state['search'].get('vendors') or []):
                site_urls = v.get('siteUrls', [])
                if site_urls and isinstance(site_urls, list) and isinstance(site_urls[0], dict):
                    vendors.append(site_urls[0].get('uri', ''))
        
        if not vendors:
            # Fallback to DOM
            vendor_links = await tk.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a')).filter(a => 
                    a.href && a.href.includes('/marketplace/') && a.href.includes('--')
                ).slice(0,20).map(a => a.href);
            }''')
            vendors = vendor_links
        
        print(f"\n  Found {len(vendors)} vendor URLs")
        
        # Scrape each vendor — INCREASING intensity
        # First 5: 3s delays (gentle)
        # Next 5: 1s delays (aggressive)
        # Last 5: 0.5s delays (abusive — should trigger detection)
        
        delays = [3.0] * 5 + [1.0] * 5 + [0.5] * 5
        vendor_targets = vendors[:min(15, len(vendors))]
        
        for i, (v_url, delay) in enumerate(zip(vendor_targets, delays), 1):
            print(f"\n  [{i}/{len(vendor_targets)}] delay={delay}s")
            
            t0 = time.time()
            
            try:
                # Navigate with minimal wait
                await tk.page.goto(v_url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(delay)
                
                status, blocks = await check_page(tk.page)
                content_len = len(await tk.page.content())
                title = await tk.page.title()
                elapsed = time.time() - t0
                
                results.append(RequestLog(
                    source='theknot', url=v_url, status=status,
                    html_size=content_len, elapsed=elapsed,
                    title=title, blocks_detected=blocks
                ))
                
                # Also try to get vendor name from state
                v_state = await tk._extract_initial_state()
                v_name = ''
                if v_state:
                    raw = (v_state.get('vendor') or {}).get('vendorRaw') or {}
                    v_name = raw.get('name', '') or (v_state.get('vendor') or {}).get('vendor', {}).get('name', '')
                
                print(f"    {status.upper()} | {v_name or title[:60]} | {content_len:,} chars | {elapsed:.1f}s")
                if blocks:
                    print(f"    ⚠️ BLOCKS: {blocks}")
                
                # If blocked twice in a row, stop being aggressive
                recent = [r for r in results[-3:] if r.status != 'ok']
                if len(recent) >= 2 and status != 'ok':
                    print("    🛑 Consecutive failures — stopping aggressive test")
                    break
                    
            except Exception as e:
                results.append(RequestLog(
                    source='theknot', url=v_url, status='error',
                    error=str(e)[:200], elapsed=time.time()-t0
                ))
                print(f"    ERROR: {e}")
    
    finally:
        await tk.stop()
    
    return results


async def stress_zola(results):
    """Test Zola pagination and intensity"""
    sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
    from zola_scraper import ZolaScraper
    
    print("\n" + "=" * 60)
    print("STRESS TEST: ZOLA (pagination test)")
    print("=" * 60)
    
    zola = ZolaScraper(output_dir=str(OUT))
    await zola.start()
    
    try:
        # Page 1
        url = "https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers"
        print(f"\n[1] Page 1...")
        await zola._goto(url, wait_after=3)
        status, blocks = await check_page(zola.page)
        content = await zola.page.content()
        next_data = await zola._extract_next_data()
        vendor_count = 0
        if next_data:
            sr = next_data.get('props', {}).get('pageProps', {}).get('searchResults', {})
            vendor_count = len(sr.get('vendors', []))
            total_hits = sr.get('totalHits', 0)
            print(f"  Total results: {total_hits}, on page: {vendor_count}")
        
        results.append(RequestLog(
            source='zola', url=url, status=status,
            html_size=len(content), title=await zola.page.title(),
            blocks_detected=blocks
        ))
        print(f"  {status.upper()} | {len(content):,} chars")
        
        # Try page 2 via URL parameter
        print(f"\n[2] Page 2...")
        url2 = "https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers?page=2"
        await zola._goto(url2, wait_after=3)
        status2, blocks2 = await check_page(zola.page)
        content2 = await zola.page.content()
        results.append(RequestLog(
            source='zola', url=url2, status=status2,
            html_size=len(content2), title=await zola.page.title(),
            blocks_detected=blocks2
        ))
        print(f"  {status2.upper()} | {len(content2):,} chars | blocks={blocks2}")
        
        # Page 3 with faster delay
        print(f"\n[3] Page 3 (fast)...")
        url3 = "https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers?page=3"
        await zola.page.goto(url3, wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1)
        status3, blocks3 = await check_page(zola.page)
        content3 = await zola.page.content()
        results.append(RequestLog(
            source='zola', url=url3, status=status3,
            html_size=len(content3), title=await zola.page.title(),
            blocks_detected=blocks3
        ))
        print(f"  {status3.upper()} | {len(content3):,} chars | blocks={blocks3}")
        
        # Rapid-fire 5 detail pages
        print(f"\n[4-8] Rapid detail pages (~1s delay)...")
        vendor_links = await zola.page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*="/wedding-vendors/wedding-photographers/"]');
            return Array.from(links).filter(a => {
                const h = a.href;
                return !h.includes('/search/') && !h.includes('/find/') && h.split('/').length > 5;
            }).slice(0,5).map(a => a.href);
        }''')
        
        for i, link in enumerate(vendor_links[:5], 4):
            t0 = time.time()
            try:
                await zola.page.goto(link, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(1)
                s, bl = await check_page(zola.page)
                cl = len(await zola.page.content())
                results.append(RequestLog(
                    source='zola', url=link, status=s,
                    html_size=cl, elapsed=time.time()-t0,
                    title=await zola.page.title(), blocks_detected=bl
                ))
                print(f"  [{i}] {s.upper()} | {cl:,} chars | {time.time()-t0:.1f}s | blocks={bl}")
            except Exception as e:
                results.append(RequestLog(
                    source='zola', url=link, status='error', error=str(e)[:200]
                ))
                print(f"  [{i}] ERROR: {e}")
    
    finally:
        await zola.stop()
    
    return results


async def stress_weddingwire(results):
    """Test WeddingWire — first load + try biz pages"""
    sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
    from weddingwire_scraper import WeddingWireScraper
    
    print("\n" + "=" * 60)
    print("STRESS TEST: WEDDINGWIRE (10 biz pages)")
    print("=" * 60)
    
    ww = WeddingWireScraper(output_dir=str(OUT))
    await ww.start()
    
    try:
        url = "https://www.weddingwire.com/wedding-photographers"
        print(f"\n[1] Category page...")
        await ww._goto(url, wait_after=5)
        status, blocks = await check_page(ww.page)
        content = await ww.page.content()
        results.append(RequestLog(
            source='weddingwire', url=url, status=status,
            html_size=len(content), title=await ww.page.title(),
            blocks_detected=blocks
        ))
        print(f"  {status.upper()} | {len(content):,} chars | blocks={blocks}")
        
        # Extract biz URLs
        biz_urls = await ww.page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href*="/biz/"]'))
                .map(a => a.href)
                .filter(h => h && h.includes('/biz/'))
                .slice(0, 10);
        }''')
        print(f"\n  Found {len(biz_urls)} biz URLs")
        
        # Scrape biz pages — 2s delays
        for i, biz_url in enumerate(biz_urls[:10], 2):
            t0 = time.time()
            try:
                await ww.page.goto(biz_url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(2)
                s, bl = await check_page(ww.page)
                cl = len(await ww.page.content())
                title = await ww.page.title()
                results.append(RequestLog(
                    source='weddingwire', url=biz_url, status=s,
                    html_size=cl, elapsed=time.time()-t0,
                    title=title, blocks_detected=bl
                ))
                print(f"  [{i}] {s.upper()} | {title[:60]} | {cl:,} chars | {time.time()-t0:.1f}s | blocks={bl}")
            except Exception as e:
                results.append(RequestLog(
                    source='weddingwire', url=biz_url, status='error',
                    error=str(e)[:200], elapsed=time.time()-t0
                ))
                print(f"  [{i}] ERROR: {e}")
    
    finally:
        await ww.stop()
    
    return results


async def main():
    print("=" * 60)
    print("WEDDING VENDOR SCRAPER — STRESS TEST")
    print(datetime.utcnow().isoformat())
    print("=" * 60)
    
    all_results = []
    
    # Test TheKnot
    await stress_theknot(all_results)
    
    # Test Zola
    await stress_zola(all_results)
    
    # Test WeddingWire
    await stress_weddingwire(all_results)
    
    # Summary
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)
    
    by_source = {}
    for r in all_results:
        by_source.setdefault(r.source, {'ok': 0, 'blocked': 0, 'captcha': 0, 'error': 0})
        s = r.status
        if s in by_source[r.source]:
            by_source[r.source][s] += 1
        else:
            by_source[r.source][s] = 1
    
    for source, counts in by_source.items():
        total = sum(counts.values())
        ok = counts.get('ok', 0)
        pct = ok * 100 / total if total > 0 else 0
        print(f"\n{source.upper()}:")
        print(f"  Total: {total}")
        print(f"  Ok: {ok} ({pct:.0f}%)")
        for k, v in sorted(counts.items()):
            if k != 'ok':
                print(f"  {k}: {v}")
    
    # Save raw results
    out_path = OUT / f"stress_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, 'w') as f:
        json.dump([asdict(r) for r in all_results], f, indent=2, default=str)
    print(f"\nRaw results: {out_path}")
    print(f"Total requests: {len(all_results)}")

if __name__ == '__main__':
    asyncio.run(main())