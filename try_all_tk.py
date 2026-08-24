"""
Try every possible TheKnot review query pattern
"""
import os, asyncio, json
from pathlib import Path

os.environ['DISPLAY'] = ':99'
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')

async def try_all():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'])
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        
        await page.goto('https://www.theknot.com/marketplace/george-street-photo-and-video-carmel-in-824253',
                       wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        ids = await page.evaluate('''() => {
            const s = window.__INITIAL_STATE__;
            if (!s || !s.vendor) return {};
            const raw = s.vendor.vendorRaw || s.vendor.vendor || {};
            return {
                uuid: raw.id || '',
                vendorId: raw.vendorId || '',
                displayId: raw.displayId || '',
                accountId: raw.accountId || '',
                locationId: raw.locationId || '',
            };
        }''')
        print(f"IDs: {json.dumps(ids)}")
        
        def try_query(field_expr, desc=""):
            """Try a GraphQL query and return result"""
            return page.evaluate('''async function({field, desc}) {
                try {
                    const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST",
                        headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                        body: JSON.stringify({query: `query { ${field} }`})
                    });
                    const d = await r.json();
                    if (d.data) return {desc, ok: true, data: JSON.stringify(d.data).slice(0, 500)};
                    return {desc, ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {desc, ok: false, error: e.message}; }
            }''', {'field': field_expr, 'desc': desc or field_expr[:60]})
        
        # Try review (singular) with different args
        print("\n=== review (singular) ===")
        for arg_name in ['vendorId', 'storefrontId', 'id', 'accountId', 'locationId', 'uuid', 'displayId']:
            for val in [ids.get('vendorId', ''), ids.get('uuid', ''), ids.get('displayId', ''), ids.get('accountId', '')]:
                if not val: continue
                r = await try_query(f'review({arg_name}: "{val}") {{ id rating text }}', f'review({arg_name}: {val[:8]})')
                if r.get('ok'):
                    print(f"  ✅ {r['desc']}: {r['data'][:300]}")
                elif 'Unknown argument' not in str(r.get('error', '')):
                    print(f"  ⚠️ {r['desc']}: {r.get('error', '')[:200]}")
        
        # Try reviews as nested field under vendor
        print("\n=== Nested queries ===")
        nest_options = [
            f'vendor(id: "{ids["vendorId"]}") {{ reviews(first: 3) {{ edges {{ node {{ id rating text }} }} }} }}',
            f'storefront(id: "{ids["uuid"]}") {{ reviews(first: 3) {{ edges {{ node {{ id rating text }} }} }} }}',
            f'account(id: "{ids["accountId"]}") {{ reviews(first: 3) {{ edges {{ node {{ id rating text }} }} }} }}',
            f'vendor(displayId: {ids["displayId"]}) {{ reviews(first: 3) {{ edges {{ node {{ id }} }} }} }}',
        ]
        for opt in nest_options:
            r = await try_query(opt, opt[:80])
            if r.get('ok'):
                print(f"  ✅ {r['desc']}: {r['data'][:300]}")
            elif 'Cannot query field' not in str(r.get('error', '')):
                print(f"  ⚠️ {r['desc']}: {r.get('error', '')[:200]}")
        
        # Try the full introspection
        print("\n=== Full introspection ===")
        schema = await page.evaluate('''async () => {
            try {
                const r = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                    method: "POST",
                    headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                    body: JSON.stringify({query: `{ __schema { queryType { fields { name args { name } } } } }`})
                });
                const d = await r.json();
                const fields = d?.data?.__schema?.queryType?.fields || [];
                return fields.filter(f => f.name.includes("review") || f.name.includes("Review") || f.name === "vendor" || f.name === "storefront");
            } catch(e) { return {error: e.message}; }
        }''')
        print(f"  Query fields: {json.dumps(schema, default=str)[:2000]}")
        
        # Also try: what if the argument is provided as a GraphQL variable?
        print("\n=== Variable-based queries ===")
        for arg_name in ['vendorId', 'storefrontId', 'id', 'entityId', 'parentId', 'targetId', 'objectId']:
            r = await page.evaluate('''async function({arg, val}) {
                const q = {
                    query: `query Q($id: ID!) { reviews(${arg}: $id, first: 3) { edges { node { id } } } }`,
                    variables: { id: val }
                };
                try {
                    const resp = await fetch("https://svc.theknotww.com/reviews-api/graphql", {
                        method: "POST", headers: {"Content-Type": "application/json", "x-tenant-id": "tk-us"},
                        body: JSON.stringify(q)
                    });
                    const d = await resp.json();
                    if (d.data) return {arg, ok: true};
                    return {arg, ok: false, error: d.errors?.[0]?.message || "no data"};
                } catch(e) { return {arg, ok: false, error: e.message}; }
            }''', {'arg': arg_name, 'val': ids['vendorId']})
            if r.get('ok'):
                print(f"  ✅ reviews({arg_name}: $id): WORKS!")
            elif 'Unknown argument' not in str(r.get('error', '')):
                print(f"  ⚠️ reviews({arg_name}): {r.get('error', '')[:200]}")
        
        await browser.close()

asyncio.run(try_all())