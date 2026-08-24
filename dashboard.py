""""
wedding_pricing_dashboard.py — Wedding Pricing Compare Full Dashboard

Merges marketplace data + vendor-specific package pricing into a single,
self-hosted web dashboard.

Usage:
  python wedding_pricing_dashboard.py [--port 8081]
  python wedding_pricing_dashboard.py --port 80 --host 0.0.0.0 (public)
"""

import json, os, sys, argparse, re
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DATA_DIR = Path.home() / 'wedding-pricing-data'
MARKETPLACE_PATH = DATA_DIR / 'pricing_latest.json'

# ── Load data ──────────────────────────────────────────────────────────────

def load_marketplace():
    path = MARKETPLACE_PATH
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)

def load_vendor_packages():
    """Load all vendor package data from various files."""
    all_packages = {}
    
    # Phase 1 package data (from vendor_packages_*.json)
    for f in sorted(DATA_DIR.glob('vendor_packages_2*.json')):
        with open(f) as fh:
            data = json.load(fh)
            for v in data:
                name = v.get('name', '')
                all_packages[name] = all_packages.get(name, {})
                all_packages[name].update({
                    'packages': v.get('packages', []),
                    'prices_found': v.get('prices_found', []) or v.get('starting_prices_raw', []),
                    'structured_data': v.get('structured_data', []),
                    'pages_scraped': v.get('pages_scraped', []),
                    'errors': v.get('errors', []),
                })
    
    # Direct vendor probe data
    direct_path = DATA_DIR / 'vendor_packages_direct.json'
    if direct_path.exists():
        with open(direct_path) as fh:
            data = json.load(fh)
            for v in data:
                name = v.get('name', '')
                all_packages[name] = all_packages.get(name, {})
                existing = all_packages[name]
                all_packages[name] = {
                    'packages': existing.get('packages', []) + v.get('packages', []),
                    'prices_found': list(set(
                        existing.get('prices_found', []) + 
                        v.get('prices_clean', []) + 
                        v.get('prices', [])
                    )),
                    'phone': v.get('phone', ''),
                    'description': v.get('description', ''),
                    'pages_ok': v.get('pages_ok', 0),
                    'website_url': v.get('url', ''),
                }
    
    # Zola websites
    for f in sorted(DATA_DIR.glob('zola_websites_*.json')):
        with open(f) as fh:
            data = json.load(fh)
            for name, info in data.items():
                if name not in all_packages:
                    all_packages[name] = {}
                all_packages[name].setdefault('phone', info.get('phone', ''))
                all_packages[name].setdefault('website_url', info.get('website_url', ''))
    
    return all_packages


# ── Hardcoded package data (from verified scraping) ────────────────────────

VERIFIED_PACKAGES = {
    'MAC Events': {
        'category': 'DJ',
        'packages': [
            {'name': 'Ceremony + Reception DJ Package', 'price': 2000, 'currency': 'USD',
             'includes': ['Professional DJ & MC', 'Ceremony + Cocktail Hour + Reception',
                         'Lighting', 'Custom playlists', 'Coordination']},
            {'name': 'Photo Booth Add-on', 'price': 250, 'currency': 'USD',
             'includes': ['Photo booth rental']},
            {'name': 'Uplighting Add-on', 'price': 550, 'currency': 'USD',
             'includes': ['Venue uplighting']},
            {'name': 'Audio Upgrade', 'price': 800, 'currency': 'USD',
             'includes': ['Premium sound system']},
        ],
        'phone': '',
        'website': 'http://maceventsindy.com',
        'market_avg': 2000,
    },
    'Blue Belles Weddings': {
        'category': 'COORD',
        'packages': [
            {'name': 'Partial Planning (Option 1)', 'price': 2250, 'currency': 'USD',
             'includes': ['Base wedding coordination', 'Selectable add-on services']},
            {'name': 'Partial Planning (Option 2)', 'price': 3500, 'currency': 'USD',
             'includes': ['Extended partial planning']},
            {'name': 'Full Planning', 'price': 7500, 'currency': 'USD',
             'includes': ['Unlimited meeting time', 'Organization resources',
                         'Vendor recommendations & contract review',
                         'Vendor meeting attendance', 'Timeline creation & execution',
                         'Event conceptualization (florals, decor, layout, signage)']},
        ],
        'phone': '(317) 426-6726',
        'website': 'https://www.bluebellesweddings.com',
        'market_avg': 1850,
    },
    'Author Audrey Weddings & Events': {
        'category': 'COORD',
        'packages': [
            {'name': 'Starter', 'price': 1250, 'currency': 'USD', 'includes': []},
            {'name': 'Essential', 'price': 2000, 'currency': 'USD', 'includes': []},
            {'name': 'Premium', 'price': 3000, 'currency': 'USD', 'includes': []},
            {'name': 'Ultimate', 'price': 5500, 'currency': 'USD', 'includes': []},
        ],
        'phone': '(812) 361-0383',
        'website': 'https://www.authoraudreymstevens.com',
        'market_avg': 500,
    },
    'Kings Court Weddings': {
        'category': 'COORD',
        'packages': [
            {'name': 'Tier 1', 'price': 925, 'currency': 'USD', 'includes': []},
            {'name': 'Tier 2', 'price': 1200, 'currency': 'USD', 'includes': []},
            {'name': 'Tier 3', 'price': 2150, 'currency': 'USD', 'includes': []},
            {'name': 'Tier 4 (Premium)', 'price': 4800, 'currency': 'USD', 'includes': []},
        ],
        'phone': '',
        'website': 'http://www.kings-court-weddings.org',
        'market_avg': 3900,
    },
    'J2 Wedding Co.': {
        'category': 'COORD',
        'packages': [
            {'name': 'Bronze', 'price': 2000, 'currency': 'USD', 'includes': []},
            {'name': 'Silver', 'price': 3000, 'currency': 'USD', 'includes': []},
            {'name': 'Gold', 'price': 4500, 'currency': 'USD', 'includes': []},
        ],
        'phone': '',
        'website': 'http://j2weddingco.com',
        'market_avg': None,
    },
    'S.H.E. - Skye High Events': {
        'category': 'COORD',
        'packages': [
            {'name': 'Standard', 'price': 3500, 'currency': 'USD', 'includes': []},
            {'name': 'Premium', 'price': 7500, 'currency': 'USD', 'includes': []},
        ],
        'phone': '',
        'website': 'https://www.sheskyehighevents.com',
        'market_avg': 7500,
    },
    'Thyme & Details': {
        'category': 'COORD',
        'packages': [
            {'name': 'Full Planning', 'price': 9500, 'currency': 'USD', 'includes': []},
            {'name': 'Premium Planning', 'price': 11000, 'currency': 'USD', 'includes': []},
        ],
        'phone': '',
        'website': 'https://www.thymeanddetails.com',
        'market_avg': 3500,
    },
    'Complete Weddings + Events Indianapolis': {
        'category': 'DJ',
        'packages': [],
        'phone': '(317) 771-4829',
        'website': 'http://www.completeindy.com',
        'market_avg': None,
        'note': 'Request-only pricing — bundles DJ + Photo + Video + Coordination',
    },
    'Higher Love Entertainment': {
        'category': 'DJ',
        'packages': [],
        'phone': '(317) 560-7912',
        'website': 'https://www.higherloveentertainment.com',
        'market_avg': 2000,
    },
    'Flower Boys': {
        'category': 'DJ',
        'packages': [],
        'phone': '(317) 735-9356',
        'website': 'https://www.flowerboysindy.com',
        'market_avg': 850,
    },
}


# ── Stats computation ──────────────────────────────────────────────────────

TIER_THRESHOLDS = {
    'DJ': {'budget': 1200, 'mid': 2500, 'label': '<$1,200 · $1,200-$2,500 · >$2,500'},
    'COORD': {'budget': 1500, 'mid': 3500, 'label': '<$1,500 · $1,500-$3,500 · >$3,500'},
    'PHOTOBOOTH': {'budget': 400, 'mid': 900, 'label': '<$400 · $400-$900 · >$900'},
}

def get_market_stats(vendors):
    stats = {}
    for v in vendors:
        cat = v.get('category', 'OTHER')
        if cat not in stats:
            s = {'category': cat, 'label': v.get('category_detail', cat), 'count': 0,
                 'with_price': 0, 'prices_min': [], 'prices_avg': [],
                 'stars': [], 'reviews': [], 'tiers': {'budget': 0, 'mid': 0, 'premium': 0, 'unknown': 0},
                 'vendors': []}
            stats[cat] = s
        s = stats[cat]
        s['count'] += 1
        s['vendors'].append(v)
        pm = v.get('starting_price_min')
        pa = v.get('starting_price_avg')
        if pm is not None:
            s['with_price'] += 1
            s['prices_min'].append(pm)
        if pa is not None:
            s['prices_avg'].append(pa)
        st = v.get('star_rating', 0)
        rc = v.get('review_count', 0)
        if st: s['stars'].append(st)
        if rc: s['reviews'].append(rc)
        tier = v.get('price_tier', 'unknown')
        s['tiers'][tier] = s['tiers'].get(tier, 0) + 1
    
    for k, s in stats.items():
        if s['prices_min']:
            p = sorted(s['prices_min'])
            s['min_price'] = min(p)
            s['max_price'] = max(p)
            s['median_price'] = p[len(p)//2]
        else:
            s['min_price'] = s['max_price'] = s['median_price'] = 0
        if s['prices_avg']:
            s['avg_price'] = sum(s['prices_avg']) / len(s['prices_avg'])
        else:
            s['avg_price'] = 0
        if s['stars']:
            s['avg_rating'] = round(sum(s['stars']) / len(s['stars']), 2)
        else:
            s['avg_rating'] = 0
        if s['reviews']:
            s['total_reviews'] = sum(s['reviews'])
        else:
            s['total_reviews'] = 0
    return stats


# ── HTML Template ──────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Wedding Pricing Compare — Indianapolis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root {
  --bg: #0f1117;
  --card: #1a1d27;
  --border: #2a2d3a;
  --text: #e4e6f0;
  --muted: #8b8fa3;
  --accent: #6366f1;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --orange: #f97316;
  --gold: #f59e0b;
  --platinum: #94a3b8;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); }
.container { max-width: 1500px; margin: 0 auto; padding: 24px; }
header { margin-bottom: 32px; }
h1 { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: var(--muted); font-size: 14px; }
.last-updated { color: var(--muted); font-size: 12px; margin-top: 2px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; margin-bottom: 32px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.card h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: var(--accent); }
.stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
.stat-row .label { color: var(--muted); }
.stat-row .value { font-weight: 600; }
.stat-row .value.green { color: var(--green); }
.stat-row .value.orange { color: var(--orange); }
.stat-row .value.red { color: var(--red); }
.tier-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.tier-budget { background: rgba(34,197,94,0.15); color: var(--green); }
.tier-mid { background: rgba(234,179,8,0.15); color: var(--yellow); }
.tier-premium { background: rgba(239,68,68,0.15); color: var(--red); }
.tier-unknown { background: rgba(139,143,163,0.15); color: var(--muted); }
.tier-counts { display: flex; gap: 8px; margin-top: 12px; }
.tier-count { flex: 1; text-align: center; padding: 8px; border-radius: 8px; font-size: 12px; background: rgba(255,255,255,0.03); }
.tier-count .num { font-size: 18px; font-weight: 700; display: block; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); color: var(--muted); font-weight: 500; position: sticky; top: 0; background: var(--card); }
td { padding: 10px 8px; border-bottom: 1px solid rgba(42,45,58,0.5); }
tr:hover td { background: rgba(99,102,241,0.05); }
.vendor-name { font-weight: 600; }
.contact-link { color: var(--accent); text-decoration: none; }
.contact-link:hover { text-decoration: underline; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; flex-wrap: wrap; }
.tab-btn { padding: 8px 16px; border: 1px solid var(--border); background: var(--card); color: var(--text); border-radius: 6px; cursor: pointer; font-size: 13px; }
.tab-btn:hover { border-color: var(--accent); }
.tab-btn.active { background: var(--accent); border-color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }
.filters { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-btn { padding: 4px 12px; border: 1px solid var(--border); border-radius: 4px; background: transparent; color: var(--muted); cursor: pointer; font-size: 12px; }
.filter-btn.active { border-color: var(--accent); color: var(--accent); }
.chart-container { max-width: 400px; margin: 0 auto 20px; }
.pkg-card { background: rgba(99,102,241,0.05); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.pkg-card h4 { font-size: 14px; font-weight: 600; margin-bottom: 4px; color: var(--accent); }
.pkg-card .price { font-size: 20px; font-weight: 700; color: var(--green); }
.pkg-card .includes { font-size: 12px; color: var(--muted); margin-top: 4px; }
.pkg-card .includes li { margin-left: 16px; margin-bottom: 2px; }
.vendor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.vendor-header .badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.badge-dj { background: rgba(99,102,241,0.15); color: var(--accent); }
.badge-coord { background: rgba(245,158,11,0.15); color: var(--gold); }
.badge-pb { background: rgba(34,197,94,0.15); color: var(--green); }
.phone-link { color: var(--accent); text-decoration: none; font-size: 13px; }
.market-placeholder { border: 2px dashed var(--border); border-radius: 12px; padding: 32px; text-align: center; color: var(--muted); }
.market-placeholder input { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; color: var(--text); font-size: 18px; width: 120px; text-align: center; margin: 8px; }
.market-placeholder .label { font-size: 13px; color: var(--muted); }
</style>
</head>
<body>
<div class="container">
<header>
  <h1>Wedding Pricing Compare</h1>
  <div class="subtitle">Indianapolis Market — DJ / MC, Coordination & Photobooth Benchmarks</div>
  <div class="last-updated">Last scrape: {{ last_scrape }} · {{ total }} vendors across {{ source_count }} sources</div>
</header>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('overview')">Market Overview</button>
  <button class="tab-btn" onclick="switchTab('vendors')">All Vendors</button>
  <button class="tab-btn" onclick="switchTab('packages')">Package Details</button>
  <button class="tab-btn" onclick="switchTab('benchmark')">Benchmark Report</button>
</div>

<div id="tab-overview" class="tab-content active">
  <div class="grid">
    {% for cat_key, s in stats.items() %}
    <div class="card">
      <h2>
        {% if cat_key == 'DJ' %}DJ / MC{% elif cat_key == 'COORD' %}Coordinator{% elif cat_key == 'PHOTOBOOTH' %}Photobooth{% else %}{{ s.label }}{% endif %}
      </h2>
      <div class="stat-row"><span class="label">Vendors tracked</span><span class="value">{{ s.count }}</span></div>
      <div class="stat-row"><span class="label">With pricing data</span><span class="value">{{ s.with_price }}</span></div>
      <div class="stat-row"><span class="label">Price range</span>
        <span class="value">{% if s.min_price %}${{ "%.0f"|format(s.min_price) }} – ${{ "%.0f"|format(s.max_price) }}{% else %}N/A{% endif %}</span>
      </div>
      <div class="stat-row"><span class="label">Median starting</span>
        <span class="value">{% if s.median_price %}${{ "%.0f"|format(s.median_price) }}{% else %}—{% endif %}</span>
      </div>
      <div class="stat-row"><span class="label">Market average</span>
        <span class="value orange">{% if s.avg_price > 0 %}${{ "%.0f"|format(s.avg_price) }}{% else %}—{% endif %}</span>
      </div>
      <div class="stat-row"><span class="label">Avg rating</span><span class="value">{{ s.avg_rating }}★</span></div>
      <div class="stat-row"><span class="label">Total reviews</span><span class="value">{{ s.total_reviews }}</span></div>
      <div class="tier-counts">
        <div class="tier-count"><span class="num" style="color:var(--green)">{{ s.tiers.get('budget',0) }}</span>Budget</div>
        <div class="tier-count"><span class="num" style="color:var(--yellow)">{{ s.tiers.get('mid',0) }}</span>Mid</div>
        <div class="tier-count"><span class="num" style="color:var(--red)">{{ s.tiers.get('premium',0) }}</span>Premium</div>
      </div>
    </div>
    {% endfor %}
  </div>

  <div class="card">
    <h2>How Your Pricing Compares</h2>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;">
      {% for cat_key, s in stats.items() %}
      <div class="market-placeholder">
        <div style="font-size:16px;font-weight:600;margin-bottom:12px;">
          {% if cat_key == 'DJ' %}DJ / MC{% elif cat_key == 'COORD' %}Coordinator{% elif cat_key == 'PHOTOBOOTH' %}Photobooth{% else %}Other{% endif %}
        </div>
        <div class="stat-row"><span class="label">Your Price</span>
          <span><input type="text" class="price-input" data-cat="{{ cat_key }}" placeholder="$$$" oninput="updatePosition(this)"></span>
        </div>
        <div class="stat-row"><span class="label">Market Avg</span><span class="value orange">{% if s.avg_price > 0 %}${{ "%.0f"|format(s.avg_price) }}{% endif %}</span></div>
        <div class="stat-row"><span class="label">Market Range</span><span class="value">{% if s.min_price %}${{ "%.0f"|format(s.min_price) }} — ${{ "%.0f"|format(s.max_price) }}{% endif %}</span></div>
        <div class="stat-row"><span class="label">Your Position</span><span class="value" id="pos-{{ cat_key }}" style="color:var(--muted)">Enter a price</span></div>
        <div class="stat-row"><span class="label">Tier</span><span class="value" id="tier-{{ cat_key }}" style="color:var(--muted)">—</span></div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>

<div id="tab-vendors" class="tab-content">
  <div class="filters">
    <button class="filter-btn active" data-cat="all" onclick="filterCat('all')">All ({{ total }})</button>
    <button class="filter-btn" data-cat="DJ" onclick="filterCat('DJ')">DJ / MC ({{ cat_counts.get('DJ',0) }})</button>
    <button class="filter-btn" data-cat="COORD" onclick="filterCat('COORD')">Coordinator ({{ cat_counts.get('COORD',0) }})</button>
    <button class="filter-btn" data-cat="PHOTOBOOTH" onclick="filterCat('PHOTOBOOTH')">Photobooth ({{ cat_counts.get('PHOTOBOOTH',0) }})</button>
  </div>
  <div style="overflow-x:auto;">
    <table>
      <thead>
        <tr><th>Vendor</th><th>Category</th><th>Source</th><th>Min Price</th><th>Avg Price</th><th>Tier</th><th>Rating</th><th>Reviews</th><th>Contact</th><th>Deals</th></tr>
      </thead>
      <tbody>
      {% for v in vendors %}
      <tr class="vendor-row" data-cat="{{ v.category }}">
        <td class="vendor-name">{{ v.name[:40] }}</td>
        <td>{% if v.category == 'DJ' %}DJ / MC{% elif v.category == 'COORD' %}Coordinator{% elif v.category == 'PHOTOBOOTH' %}Photobooth{% else %}{{ v.category_detail }}{% endif %}</td>
        <td style="font-size:11px;color:var(--muted)">{{ v.source }}</td>
        <td>{% if v.starting_price_min is not none %}${{ "%.0f"|format(v.starting_price_min) }}{% else %}—{% endif %}</td>
        <td>{% if v.starting_price_avg is not none %}${{ "%.0f"|format(v.starting_price_avg) }}{% else %}—{% endif %}</td>
        <td><span class="tier-badge tier-{{ v.price_tier }}">{{ v.price_tier }}</span></td>
        <td>{% if v.star_rating > 0 %}{{ v.star_rating }}★{% else %}—{% endif %}</td>
        <td>{{ v.review_count }}</td>
        <td>
          {% if v.website_url and 'theknot.com' not in v.website_url and 'zola.com' not in v.website_url %}
            <a class="contact-link" href="{{ v.website_url }}" target="_blank">website</a>
          {% endif %}
          {% if v.phone %}<span style="font-size:11px;display:block">{{ v.phone }}</span>{% endif %}
        </td>
        <td>{% if v.deal_count > 0 %}<span style="color:var(--orange);font-size:11px">{{ v.deal_count }} deals</span>{% endif %}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<div id="tab-packages" class="tab-content">
  <div class="filters">
    <button class="filter-btn active" data-pkgcat="all" onclick="filterPkgCat('all')">All</button>
    <button class="filter-btn" data-pkgcat="DJ" onclick="filterPkgCat('DJ')">DJ / MC</button>
    <button class="filter-btn" data-pkgcat="COORD" onclick="filterPkgCat('COORD')">Coordinators</button>
  </div>
  <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(380px,1fr));">
    {% for pkg in package_vendors %}
    <div class="card pkg-vendor" data-pkgcat="{{ pkg.category }}">
      <div class="vendor-header">
        <div>
          <div style="font-size:14px;font-weight:600">{{ pkg.name }}</div>
          <div style="font-size:12px;color:var(--muted);margin-top:2px">
            {% if pkg.website %}<a href="{{ pkg.website }}" target="_blank" style="color:var(--accent);text-decoration:none">website</a>{% endif %}
            {% if pkg.phone %} · <span>{{ pkg.phone }}</span>{% endif %}
            {% if pkg.market_avg %} · <span style="color:var(--orange)">Market: ${{ "%.0f"|format(pkg.market_avg) }}</span>{% endif %}
          </div>
        </div>
        <span class="badge badge-{% if pkg.category == 'DJ' %}dj{% elif pkg.category == 'COORD' %}coord{% else %}pb{% endif %}">{{ pkg.category }}</span>
      </div>
      {% if pkg.note %}
      <div style="padding:8px;background:rgba(249,115,22,0.1);border-radius:6px;font-size:13px;color:var(--orange);margin-bottom:8px">{{ pkg.note }}</div>
      {% endif %}
      {% if pkg.packages %}
        {% for p in pkg.packages %}
        <div class="pkg-card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <h4>{{ p.name }}</h4>
            <span class="price">${{ "%.0f"|format(p.price) }}</span>
          </div>
          {% if p.includes and p.includes|length > 0 %}
          <ul class="includes">
            {% for inc in p.includes %}<li>{{ inc }}</li>{% endfor %}
          </ul>
          {% endif %}
        </div>
        {% endfor %}
      {% else %}
        <div style="font-size:13px;color:var(--muted);padding:8px;">No public package pricing available</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</div>

<div id="tab-benchmark" class="tab-content">
  {% for cat_key, s in stats.items() %}
  {% if s.with_price > 0 %}
  <div class="card" style="margin-bottom:16px;">
    <h2>{% if cat_key == 'DJ' %}DJ / MC{% elif cat_key == 'COORD' %}Coordinator{% else %}{{ s.label }}{% endif %} — Market Benchmark</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <div>
        <h3 style="font-size:14px;color:var(--muted);margin-bottom:12px;">Pricing Distribution</h3>
        <canvas id="chart-{{ cat_key }}" height="200"></canvas>
        <div style="margin-top:12px;font-size:12px;color:var(--muted);">
          {{ tier_labels.get(cat_key, '') }}
        </div>
      </div>
      <div>
        <h3 style="font-size:14px;color:var(--muted);margin-bottom:12px;">Top Vendors by Reviews</h3>
        <table style="font-size:12px;">
          <thead><tr><th>Vendor</th><th>Price</th><th>Tier</th><th>Rating</th><th>Reviews</th></tr></thead>
          <tbody>
          {% for v in top_vendors.get(cat_key, []) %}
          <tr><td>{{ v.display_name }}</td><td>{% if v.starting_price_min is not none %}${{ "%.0f"|format(v.starting_price_min) }}{% else %}—{% endif %}</td><td><span class="tier-badge tier-{{ v.price_tier }}">{{ v.price_tier }}</span></td><td>{{ v.star_rating }}★</td><td>{{ v.review_count }}</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  {% endif %}
  {% endfor %}
</div>

<script>
function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  document.querySelector('.tab-btn[onclick*="'+tab+'"]').classList.add('active');
  setTimeout(() => { drawCharts(); }, 50);
}

function filterCat(cat) {
  document.querySelectorAll('.filter-btn[data-cat]').forEach(el => el.classList.remove('active'));
  document.querySelector(`.filter-btn[data-cat="${cat}"]`).classList.add('active');
  document.querySelectorAll('.vendor-row').forEach(row => {
    row.style.display = (cat === 'all' || row.dataset.cat === cat) ? '' : 'none';
  });
}

function filterPkgCat(cat) {
  document.querySelectorAll('.filter-btn[data-pkgcat]').forEach(el => el.classList.remove('active'));
  document.querySelector(`.filter-btn[data-pkgcat="${cat}"]`).classList.add('active');
  document.querySelectorAll('.pkg-vendor').forEach(el => {
    el.style.display = (cat === 'all' || el.dataset.pkgcat === cat) ? '' : 'none';
  });
}

function updatePosition(input) {
  const cat = input.dataset.cat;
  const val = parseFloat(input.value.replace(/[^0-9.]/g, ''));
  const pos = document.getElementById('pos-'+cat);
  const tier = document.getElementById('tier-'+cat);
  if (!val || isNaN(val)) { pos.textContent = 'Enter a price'; pos.style.color = ''; tier.textContent = '—'; return; }
  
  const stats = {{ chart_data|safe }};
  const catStats = stats[cat];
  if (!catStats || !catStats.avg_price) { pos.textContent = 'No data'; return; }
  
  const avg = catStats.avg_price;
  const minP = catStats.min_price || 0;
  const maxP = catStats.max_price || 5000;
  const pct = ((val - minP) / (maxP - minP)) * 100;
  
  if (val < avg * 0.85) { pos.textContent = 'Below market'; pos.style.color = 'var(--green)'; }
  else if (val > avg * 1.15) { pos.textContent = 'Above market'; pos.style.color = 'var(--red)'; }
  else { pos.textContent = 'At market'; pos.style.color = 'var(--yellow)'; }
  
  // Tier
  const thresholds = {{ tier_thresholds|safe }};
  const t = thresholds[cat] || {};
  if (val < (t.budget || 999)) tier.textContent = 'Budget'; else if (val < (t.mid || 9999)) tier.textContent = 'Mid'; else tier.textContent = 'Premium';
}

const chartData = {{ chart_json|safe }};
const charts = {};

function drawCharts() {
  for (const [cat, data] of Object.entries(chartData)) {
    const el = document.getElementById('chart-'+cat);
    if (!el) continue;
    if (charts[cat]) { charts[cat].destroy(); }
    if (!data.labels || data.labels.length === 0) continue;
    charts[cat] = new Chart(el, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Vendors',
          data: data.values,
          backgroundColor: data.colors,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1, color: '#8b8fa3' }, grid: { color: '#2a2d3a' } },
          x: { ticks: { color: '#8b8fa3' }, grid: { display: false } }
        }
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', drawCharts);
</script>
</div>
</body>
</html>"""

# ── Routes ──

@app.route('/')
def index():
    data = load_marketplace()
    total = len(data)
    sources = set(v.get('source', '?') for v in data)
    source_count = len(sources)
    
    if MARKETPLACE_PATH.exists():
        mtime = datetime.fromtimestamp(MARKETPLACE_PATH.stat().st_mtime)
        last_scrape = mtime.strftime('%b %d, %Y at %I:%M %p')
    else:
        last_scrape = 'Never'
    
    stats = get_market_stats(data)
    
    # Category counts for filter buttons
    cat_counts = {}
    for v in data:
        c = v.get('category', 'OTHER')
        cat_counts[c] = cat_counts.get(c, 0) + 1
    
    # Add display_name to all vendors
    for v in data:
        v['display_name'] = v.get('name', '')[:30]
    
    # Top vendors by review count
    top_vendors = {}
    for cat_key, s in stats.items():
        sorted_v = sorted(s['vendors'], key=lambda x: x.get('review_count', 0) or 0, reverse=True)[:5]
        top_vendors[cat_key] = sorted_v
    
    # Tier thresholds for JS
    tier_thresholds = {}
    for k, v in TIER_THRESHOLDS.items():
        tier_thresholds[k] = {'budget': v['budget'], 'mid': v['mid']}
    
    # Tier labels
    tier_labels = {}
    for k, v in TIER_THRESHOLDS.items():
        tier_labels[k] = v['label']
    
    # Chart data
    chart_data = {}
    for cat_key, s in stats.items():
        if not s.get('with_price', 0):
            chart_data[cat_key] = {'labels': [], 'values': [], 'colors': [],
                                   'avg_price': s.get('avg_price', 0),
                                   'min_price': s.get('min_price', 0),
                                   'max_price': s.get('max_price', 0)}
            continue
        prices = sorted(s.get('prices_min', []))
        if prices and len(prices) > 1:
            step = max(1, (prices[-1] - prices[0]) / 5)
            bins = {}
            for p in prices:
                bin_key = int((p - prices[0]) / step) if step > 0 else 0
                bin_label = f"${prices[0] + bin_key*step:.0f}"
                bins[bin_key] = bins.get(bin_key, 0) + 1
            sorted_bins = sorted(bins.items())
            chart_data[cat_key] = {
                'labels': [f"${(prices[0] + k*step):.0f}" for k, _ in sorted_bins],
                'values': [v for _, v in sorted_bins],
                'colors': ['#6366f1' for _ in sorted_bins],
                'avg_price': s.get('avg_price', 0),
                'min_price': s.get('min_price', 0),
                'max_price': s.get('max_price', 0),
            }
        else:
            chart_data[cat_key] = {'labels': [], 'values': [], 'colors': [],
                                   'avg_price': s.get('avg_price', 0),
                                   'min_price': s.get('min_price', 0),
                                   'max_price': s.get('max_price', 0)}
    
    # Package vendors (verified)
    package_vendors = list(VERIFIED_PACKAGES.values())
    # Sort by category then market_avg
    package_vendors.sort(key=lambda x: (x.get('category', ''), x.get('market_avg') or 99999))
    
    # Add zola websites from marketplace data
    for v in data:
        if v.get('clean_url') and v.get('name') not in [p['name'] for p in package_vendors]:
            pass  # Only show verified packages for now
    
    return render_template_string(
        HTML,
        stats=stats,
        vendors=data,
        total=total,
        source_count=source_count,
        sources=list(sources),
        last_scrape=last_scrape,
        cat_counts=cat_counts,
        top_vendors=top_vendors,
        tier_labels=tier_labels,
        tier_thresholds=json.dumps(tier_thresholds),
        chart_data=chart_data,
        chart_json=json.dumps(chart_data),
        package_vendors=package_vendors,
    )

@app.route('/api/data')
def api_data():
    return jsonify(load_marketplace())

@app.route('/api/stats')
def api_stats():
    return jsonify(get_market_stats(load_marketplace()))

@app.route('/api/packages')
def api_packages():
    return jsonify(list(VERIFIED_PACKAGES.values()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wedding Pricing Dashboard')
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    print(f"Wedding Pricing Dashboard: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)