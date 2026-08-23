"""
Explore Zola vendor detail structure
"""
import json
from pathlib import Path

out = Path('/home/alex/code/BUTTERGANG/theknot-scraper/output')

with open(out / 'zola_vendor_detail_next_data.json') as f:
    data = json.load(f)

storefront = data.get('props', {}).get('pageProps', {}).get('storefront', {})
print(f"Storefront keys ({len(storefront)}):")
for k, v in storefront.items():
    if v is not None and v != "" and v != [] and v != {}:
        s = json.dumps(v, default=str)
        if len(s) > 500:
            s = s[:500] + "..."
        print(f"  {k}: {s}")
    else:
        print(f"  {k}: [{type(v).__name__}]")

# Check search results structure
print(f"\n== SEARCH RESULTS STRUCTURE ==")
with open(out / 'zola_next_data.json') as f:
    search_data = json.load(f)

search_results = search_data.get('props', {}).get('pageProps', {}).get('searchResults', {})
vendors = search_results.get('vendors', [])
print(f"Total results: {search_results.get('totalHits')}")  
print(f"Vendors returned: {len(vendors)}")

if vendors:
    v = vendors[0]
    print(f"\nSample vendor keys: {list(v.keys())}")
    for k in v:
        val = v[k]
        s = json.dumps(val, default=str)
        if len(s) > 200:
            s = s[:200] + "..."
        print(f"  {k}: {s}")