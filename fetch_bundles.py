"""Fetch TheKnot webpack bundles to find the actual review GraphQL query
"""
import os, asyncio, re, json, urllib.request
from pathlib import Path

BASE = 'https://www.theknot.com/static/xo-marketplace/monorepo_assets/'

BUNDLES = [
    'apps_marketplace-web_api_graphql_Storefront_a-470545.e6367ee5c8d05b74adcd.bundle.js',
    'apps_marketplace-web_api_paiver_index_ts-apps_marketplace-web_api_paiverRos_index_ts-apps_mar-949d90.e6367ee5c8d05b74adcd.bundle.js',
]

def main():
    print("Fetching bundle files to find review GraphQL queries...\n")
    
    for bundle in BUNDLES:
        url = BASE + bundle
        print(f"--- {bundle[:80]} ---")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode('utf-8', errors='replace')
            
            print(f"  Size: {len(text):,} chars")
            
            # Search for GraphQL query strings mentioning review
            for p in [r'query\s+\w{0,40}\s*\([^)]{0,200}\)\s*\{[^}]{0,300}review[^}]{0,500}',
                      r'["\']query["\']\s*:\s*["\'][^"\']{0,300}review[^"\']{0,500}["\']',
                      r'gql`[^`]{0,500}review[^`]{0,500}`',
                      r'operationName["\']\s*:\s*["\'][^"\']*Review[^"\']*["\']']:
                for m in re.finditer(p, text, re.DOTALL):
                    print(f"  Match: {m.group()[:400]}...\n")
            
            # Search for reviews() field calls
            for m in re.finditer(r'reviews\s*\([^)]{0,300}\)', text):
                print(f"  reviews arg: {m.group()[:200]}")
            
            # Search for gql template literals
            for m in re.finditer(r'gql`[^`]{0,1500}`', text):
                g = m.group()
                if 'review' in g.lower() or 'Review' in g:
                    print(f"  gql review query: {g[:600]}")
            
            # Search for fragments
            for m in re.finditer(r'fragment\s+\w+[^}]{0,500}review[^}]{0,500}', text):
                print(f"  fragment: {m.group()[:300]}")
                    
        except Exception as e:
            print(f"  Error: {e}")
        print()

main()