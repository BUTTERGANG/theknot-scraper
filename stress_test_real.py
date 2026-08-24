"""
REAL STRESS TEST — find actual rate limits and blocks
Tests by scraping until TRUE blocks appear (not false positive keyword scripts)

Strategy:
1. Hammer TheKnot vendor pages with decreasing delays
2. Check for REAL blocks (short/empty HTML, 403 text, CAPTCHA, access denied)
3. Record the exact point where it breaks
"""
import asyncio, json, os, sys, time
from pathlib import Path
from datetime import datetime

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

OUT = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output/stress')
OUT.mkdir(exist_ok=True, parents=True)

# Real block indicators (short pages with actual error messages)
REAL_BLOCKS = [
    '403 forbidden', 'access denied', 'you have been blocked',
    'your access has been blocked', 'unusual traffic from your',
    'please verify you are a human', 'please complete the security check',
    'just a moment...',  # Cloudflare challenge page
    'enable javascript', 'enable cookies',
]

async def real_check(page) -> dict:
    """Check for REAL blocking — not just security script presence"""
    title = ''
    content = ''
    body = ''
    try:
        title = (await page.title() or '').lower()
        content = await page.content()
        body = await page.inner_text('body')
    except:
        pass
    
    html_mb = len(content) / 1024 / 1024
    body_lower = (body or '').lower()
    
    # REAL blocks have short HTML + block keywords
    for kw in REAL_BLOCKS:
        if kw in body_lower or kw in content.lower():
            return {
                'blocked': True,
                'reason': kw,
                'html_mb': round(html_mb, 1),
                'title': title[:80],
            }
    
    # Cloudflare/DataDome challenge pages are usually <200KB with minimal content
    if html_mb < 0.2 and (title and ('challenge' in title or 'captcha' in title or 'verify' in title)):
        return {
            'blocked': True,
            'reason': 'short_challenge_page',
            'html_mb': round(html_mb, 1),
            'title': title[:80],
        }
    
    return {
        'blocked': False,
        'reason': '',
        'html_mb': round(html_mb, 1),
        'title': title[:80],
    }


async def test_single_source(name, base_urls, n_vendors, delays_schedule, start_urls=None):
    """
    Test one source with a schedule of increasing aggression.
    delays_schedule: list of (delay_before_next, description) tuples
    """
    from playwright.async_api import async_playwright
    
    print(f"\n{'='*70}")
    print(f"REAL STRESS TEST: {name}")
    print(f"{'='*70}")
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        all_urls = []
        if start_urls:
            # Pre-fetch vendor list
            print("\n[Phase 0] Pre-fetching vendor list...")
            await page.goto(base_urls[0], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            if 'theknot' in name.lower():
                try:
                    state = await page.evaluate('() => window.__INITIAL_STATE__')
                    if state and state.get('search', {}).get('vendors'):
                        for v in state['search']['vendors']:
                            site_urls = v.get('siteUrls', [])
                            if site_urls and isinstance(site_urls[0], dict):
                                all_urls.append(site_urls[0].get('uri', ''))
                except:
                    pass
                
                if not all_urls:
                    all_urls = await page.evaluate('''() =>
                        Array.from(document.querySelectorAll('a[href*="/marketplace/"][href*="--"]'))
                        .map(a => a.href).slice(0,30)
                    ''')
            
            elif 'zola' in name.lower():
                try:
                    nd = await page.evaluate('() => { const e = document.getElementById("__NEXT_DATA__"); return e ? JSON.parse(e.textContent) : null; }')
                    if nd:
                        vends = nd.get('props', {}).get('pageProps', {}).get('searchResults', {}).get('vendors', [])
                        for v in vends:
                            slug = v.get('slug', '')
                            if slug:
                                all_urls.append(f"https://www.zola.com/wedding-vendors/wedding-photographers/{slug}")
                except:
                    pass
            
            elif 'weddingwire' in name.lower():
                # Get biz URLs from search page
                # WeddingWire now has Cloudflare challenge — but pages still load
                links = await page.evaluate('''() => 
                    Array.from(document.querySelectorAll('a[href*="/biz/"]'))
                    .map(a => a.href).filter(h => h)
                    .slice(0, 30)
                ''')
                all_urls = links
            
            if not all_urls:
                all_urls = start_urls[:n_vendors] if start_urls else base_urls 
        
        if not all_urls:
            all_urls = base_urls
        
        all_urls = all_urls[:n_vendors]
        print(f"  Loaded {len(all_urls)} vendor URLs")
        
        # Run through delays schedule
        idx = 0
        for delay_sec, phase_name in delays_schedule:
            batch_size = min(n_vendors - idx, 5) if idx < n_vendors else 0
            if batch_size <= 0:
                break
            
            print(f"\n[Phase {phase_name}] delay={delay_sec}s, batch={batch_size} vendors")
            
            for i in range(batch_size):
                if idx >= len(all_urls):
                    break
                
                url = all_urls[idx]
                t0 = time.time()
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                    await asyncio.sleep(delay_sec)
                    
                    result = await real_check(page)
                    result['url'] = url
                    result['elapsed'] = round(time.time() - t0, 1)
                    result['phase'] = phase_name
                    results.append(result)
                    
                    indicator = '🚫 BLOCKED' if result['blocked'] else '✅ OK'
                    print(f"  [{idx+1}/{len(all_urls)}] {indicator} {result['html_mb']}MB {result['elapsed']}s {result['reason'] if result['blocked'] else ''}")
                    if not result['blocked']:
                        # Print vendor name if available
                        pass
                    
                    # If real block, end aggressive testing
                    if result['blocked']:
                        print(f"\n  ⚠️ REAL BLOCK at vendor {idx+1} (phase {phase_name})")
                        # Don't stop entirely — continue with slower delays
                
                except Exception as e:
                    results.append({
                        'blocked': True,
                        'reason': str(e)[:100],
                        'html_mb': 0,
                        'url': url,
                        'elapsed': round(time.time() - t0, 1),
                        'phase': phase_name,
                        'title': f'ERROR: {str(e)[:60]}',
                    })
                    print(f"  [{idx+1}/{len(all_urls)}] ❌ ERROR: {str(e)[:60]}")
                
                idx += 1
        
        await browser.close()
    
    # Summary
    ok_count = sum(1 for r in results if not r['blocked'])
    blocked_count = sum(1 for r in results if r['blocked'])
    real_blocked = sum(1 for r in results if r['blocked'] and r['html_mb'] < 0.5)
    false_pos = sum(1 for r in results if r['blocked'] and r['html_mb'] >= 0.5)
    
    print(f"\n--- {name} Summary ---")
    print(f"  Requests: {len(results)}")
    print(f"  Real blocks (short page + keywords): {real_blocked}")
    print(f"  False positives (big pages with scripts): {false_pos}")
    print(f"  Successful: {ok_count}")
    
    if real_blocked > 0:
        first = [r for r in results if r['blocked'] and r['html_mb'] < 0.5]
        print(f"  ⚠️ First real block at index {results.index(first[0])} (phase {first[0].get('phase', '?')})")
    
    # Save
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = OUT / f"stress_{name.lower().replace(' ', '_')}_{ts}.json"
    with open(path, 'w') as f:
        json.dump({'source': name, 'results': results}, f, indent=2, default=str)
    print(f"  Saved: {path}")
    
    return results


async def main():
    print("=" * 70)
    print("REAL STRESS TEST — find actual rate limits")
    print(datetime.utcnow().isoformat())
    print("=" * 70)
    
    # === THEKNOT: 20 vendors, gentle→aggressive ===
    tk_delays = [
        (4.0, '1-gentle'),
        (2.0, '2-moderate'),
        (1.0, '3-aggressive'),
        (0.5, '4-abusive'),
    ]
    tk_results = await test_single_source(
        'TheKnot',
        ['https://www.theknot.com/marketplace/wedding-photographers-indianapolis-in'],
        n_vendors=20,
        delays_schedule=tk_delays,
        start_urls=[]
    )
    
    # === ZOLA: 15 vendors ===
    zola_delays = [
        (4.0, '1-gentle'),
        (1.5, '2-moderate'),
        (0.7, '3-aggressive'),
    ]
    zola_results = await test_single_source(
        'Zola',
        ['https://www.zola.com/wedding-vendors/search/new-york-ny--wedding-photographers'],
        n_vendors=15,
        delays_schedule=zola_delays,
        start_urls=[]
    )
    
    # === WEDDINGWIRE: 15 biz pages ===
    ww_delays = [
        (4.0, '1-gentle'),
        (2.0, '2-moderate'),
        (1.0, '3-aggressive'),
    ]
    ww_results = await test_single_source(
        'WeddingWire',
        ['https://www.weddingwire.com/wedding-photographers'],
        n_vendors=15,
        delays_schedule=ww_delays,
        start_urls=[]
    )
    
    # === OVERALL SUMMARY ===
    print("\n" + "=" * 70)
    print("OVERALL STRESS TEST RESULTS")
    print("=" * 70)
    
    all_sources = [
        ('TheKnot', tk_results),
        ('Zola', zola_results),
        ('WeddingWire', ww_results),
    ]
    
    for name, results in all_sources:
        if not results:
            print(f"\n{name}: NO DATA")
            continue
        ok = sum(1 for r in results if not r['blocked'])
        bad = sum(1 for r in results if r['blocked'])
        real = sum(1 for r in results if r['blocked'] and r['html_mb'] < 0.5)
        false = sum(1 for r in results if r['blocked'] and r['html_mb'] >= 0.5)
        total = len(results)
        print(f"\n{name}: {total} total | {ok} OK ({ok*total//100}%) | {bad} flagged | {real} real blocks | {false} false positives")
        
        # Find first real block
        real_blocked = [r for r in results if r['blocked'] and r['html_mb'] < 0.5]
        if real_blocked:
            first = real_blocked[0]
            idx = results.index(first)
            print(f"  First real block: request #{idx+1} (phase {first.get('phase', '?')}) — {first.get('reason', '')}")
        else:
            print(f"  ✅ No real blocks detected — all content loaded successfully")
    
    print("\n✅ Stress test complete")

if __name__ == '__main__':
    asyncio.run(main())