"""
STRESS TEST v3 — use the actual scrapers at scale
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/stress')
OUT.mkdir(exist_ok=True, parents=True)

async def stress_theknot():
    """TheKnot: 20 vendor detail pages — 4 phases of 5"""
    sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
    from theknot_scraper_v2 import TheKnotScraperV2
    
    print("\n" + "=" * 70)
    print("THEKNOT STRESS — 20 vendors across 4 phases")
    print("=" * 70)
    
    tk = TheKnotScraperV2(output_dir=str(OUT))
    await tk.start()
    
    results = []
    try:
        # Get vendor URLs
        vendors = await tk.search_marketplace('indianapolis', 'wedding-photographers', 'in')
        urls = [v.theknot_url for v in vendors[:20] if v.theknot_url]
        print(f"  Got {len(urls)} vendor URLs to scrape")
        
        # Phase 1: 5 vendors @ 4s delay (gentle)
        # Phase 2: 5 vendors @ 2s delay (moderate)
        # Phase 3: 5 vendors @ 1s delay (aggressive)
        # Phase 4: 5 vendors @ 0.5s delay (abusive)
        delays = [4.0]*5 + [2.0]*5 + [1.0]*5 + [0.5]*5
        
        for i, (url, delay) in enumerate(zip(urls, delays)):
            t0 = time.time()
            try:
                await tk.page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(delay)
                
                content = await tk.page.content()
                body = await tk.page.inner_text('body')
                title = await tk.page.title()
                elapsed = time.time() - t0
                
                html_mb = len(content) / 1024 / 1024
                
                # Check for real block
                blocked = False
                reason = ''
                body_lower = body.lower() if body else ''
                for kw in ['403 forbidden', 'access denied', 'you have been blocked',
                          'unusual traffic', 'please verify you are a human', 'captcha']:
                    if kw in body_lower or kw in content.lower():
                        blocked = True
                        reason = kw
                        break
                
                # Also check if it's a short empty page (real block)
                if html_mb < 0.2 and not title:
                    blocked = True
                    reason = 'empty_page'
                
                # Try to extract vendor name
                v_name = ''
                try:
                    state = await tk.page.evaluate('() => window.__INITIAL_STATE__')
                    if state:
                        raw = (state.get('vendor') or {}).get('vendorRaw') or {}
                        v_name = raw.get('name', '')
                except:
                    pass
                
                result = {
                    'idx': i+1, 'phase': 'gentle' if i < 5 else 'moderate' if i < 10 else 'aggressive' if i < 15 else 'abusive',
                    'delay': delay, 'url': url[:100], 'vendor': v_name or title[:60],
                    'html_mb': round(html_mb, 2), 'elapsed': round(elapsed, 1),
                    'blocked': blocked, 'reason': reason,
                }
                results.append(result)
                
                indicator = '🚫' if blocked else '✅'
                print(f"  [{i+1:2d}] {indicator} {v_name or title[:50]:40s} {html_mb:.1f}MB delay={delay}s {elapsed:.1f}s" + (f' ⚠️{reason}' if blocked else ''))
                
                if blocked:
                    print(f"         ⚠️ BLOCKED at vendor {i+1} — {reason}")
                    
            except Exception as e:
                results.append({
                    'idx': i+1, 'phase': 'gentle' if i < 5 else 'moderate' if i < 10 else 'aggressive' if i < 15 else 'abusive',
                    'delay': delay, 'url': str(url)[:100], 'vendor': '',
                    'html_mb': 0, 'elapsed': round(time.time() - t0, 1),
                    'blocked': True, 'reason': f'error: {str(e)[:80]}',
                })
                print(f"  [{i+1:2d}] ❌ ERROR: {str(e)[:60]}")
        
        # Save
        path = OUT / f"stress_theknot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        ok = sum(1 for r in results if not r['blocked'])
        blocked = sum(1 for r in results if r['blocked'])
        print(f"\n  TheKnot: {len(results)} requests | {ok} OK | {blocked} blocked")
        print(f"  Saved: {path}")
        
    finally:
        await tk.stop()
    
    return results


async def stress_zola():
    """Zola: 15 vendor detail pages — 3 phases of 5"""
    sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
    from zola_scraper import ZolaScraper
    
    print("\n" + "=" * 70)
    print("ZOLA STRESS — 15 detail pages across 3 phases")
    print("=" * 70)
    
    zola = ZolaScraper(output_dir=str(OUT))
    await zola.start()
    
    results = []
    try:
        # Get vendor URLs from search
        await zola._goto('https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers', 5)
        nd = await zola._extract_next_data()
        vendors = []
        if nd:
            vends = nd.get('props', {}).get('pageProps', {}).get('searchResults', {}).get('vendors', [])
            for v in vends[:15]:
                slug = v.get('slug', '')
                if slug:
                    vendors.append(f"https://www.zola.com/wedding-vendors/wedding-photographers/{slug}")
        
        print(f"  Got {len(vendors)} vendor URLs to scrape")
        
        delays = [4.0]*5 + [1.5]*5 + [0.7]*5
        
        for i, (url, delay) in enumerate(zip(vendors, delays)):
            t0 = time.time()
            try:
                await zola.page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(delay)
                
                content = await zola.page.content()
                body = await zola.page.inner_text('body')
                title = await zola.page.title()
                elapsed = time.time() - t0
                html_mb = len(content) / 1024 / 1024
                
                blocked = False
                reason = ''
                body_lower = body.lower() if body else ''
                for kw in ['403 forbidden', 'access denied', 'you have been blocked',
                          'unusual traffic', 'please verify you are a human', 'captcha']:
                    if kw in body_lower or kw in content.lower():
                        blocked = True
                        reason = kw
                        break
                if html_mb < 0.2 and not title:
                    blocked = True
                    reason = 'empty_page'
                
                # Get vendor name
                v_name = ''
                nd2 = await zola._extract_next_data()
                if nd2:
                    sf = nd2.get('props', {}).get('pageProps', {}).get('storefront', {})
                    v_name = sf.get('name', '') if isinstance(sf, dict) else ''
                
                result = {
                    'idx': i+1, 'phase': 'gentle' if i < 5 else 'moderate' if i < 10 else 'aggressive',
                    'delay': delay, 'url': url[:100], 'vendor': v_name or title[:60],
                    'html_mb': round(html_mb, 2), 'elapsed': round(elapsed, 1),
                    'blocked': blocked, 'reason': reason,
                }
                results.append(result)
                
                indicator = '🚫' if blocked else '✅'
                print(f"  [{i+1:2d}] {indicator} {v_name or title[:50]:40s} {html_mb:.1f}MB delay={delay}s {elapsed:.1f}s" + (f' ⚠️{reason}' if blocked else ''))
                
            except Exception as e:
                results.append({
                    'idx': i+1, 'phase': 'gentle' if i < 5 else 'moderate' if i < 10 else 'aggressive',
                    'delay': delay, 'url': str(url)[:100], 'vendor': '',
                    'html_mb': 0, 'elapsed': round(time.time() - t0, 1),
                    'blocked': True, 'reason': f'error: {str(e)[:80]}',
                })
                print(f"  [{i+1:2d}] ❌ ERROR: {str(e)[:60]}")
        
        path = OUT / f"stress_zola_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        ok = sum(1 for r in results if not r['blocked'])
        blocked = sum(1 for r in results if r['blocked'])
        print(f"\n  Zola: {len(results)} requests | {ok} OK | {blocked} blocked")
        print(f"  Saved: {path}")
        
    finally:
        await zola.stop()
    
    return results


async def main():
    print("=" * 70)
    print("STRESS TEST v3 — real scrapers at scale")
    print(datetime.utcnow().isoformat())
    print("=" * 70)
    
    all_results = {}
    
    all_results['theknot'] = await stress_theknot()
    all_results['zola'] = await stress_zola()
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    for name, results in all_results.items():
        if not results:
            print(f"\n{name}: NO DATA")
            continue
        ok = sum(1 for r in results if not r['blocked'])
        blocked = sum(1 for r in results if r['blocked'])
        total = len(results)
        print(f"\n{name.upper()}: {total} total | {ok} OK ({ok*100//total}%) | {blocked} blocked")
        
        if blocked:
            first_blocked = [r for r in results if r['blocked']]
            if first_blocked:
                fb = first_blocked[0]
                print(f"  First block at request #{fb['idx']} (phase: {fb['phase']}, delay: {fb['delay']}s)")
                print(f"  Reason: {fb['reason']}")
        
        # By phase
        for phase in ['gentle', 'moderate', 'aggressive', 'abusive']:
            phase_results = [r for r in results if r.get('phase') == phase]
            if phase_results:
                phase_ok = sum(1 for r in phase_results if not r['blocked'])
                print(f"  Phase {phase}: {phase_ok}/{len(phase_results)} OK ({phase_ok*100//len(phase_results)}%)")
    
    print("\n✅ Done")

if __name__ == '__main__':
    asyncio.run(main())