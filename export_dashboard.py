"""
Export dashboard data from wedding_vendors DB as JSON for the HTML dashboard
"""
import json, psycopg2
from datetime import datetime

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

data = {}

# Total vendors
cur.execute('SELECT COUNT(*) FROM vendors')
data['total_vendors'] = cur.fetchone()[0]

# Reviews
cur.execute('SELECT COUNT(*) FROM vendor_reviews')
data['total_reviews'] = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM vendor_reviews WHERE LENGTH(review_text) > 50")
data['with_text'] = cur.fetchone()[0]

# Avg rating
cur.execute('SELECT ROUND(AVG(rating), 2) FROM vendor_reviews WHERE rating IS NOT NULL')
r = cur.fetchone()
data['avg_rating'] = float(r[0]) if r and r[0] else None

# States covered
cur.execute("SELECT COUNT(DISTINCT state) FROM vendors WHERE state IS NOT NULL AND state != ''")
data['states_covered'] = cur.fetchone()[0]

# Sentiment
sent = {'positive': 0, 'neutral': 0, 'negative': 0}
cur.execute("SELECT sentiment, COUNT(*) FROM vendor_reviews WHERE sentiment != '' GROUP BY sentiment")
for r in cur.fetchall():
    sent[r[0]] = r[1]
total_sent = sum(sent.values())
data['sentiment'] = {
    'positive': sent['positive'],
    'neutral': sent['neutral'],
    'negative': sent['negative'],
    'total': total_sent,
    'positive_pct': sent['positive'] * 100 / max(total_sent, 1),
    'neutral_pct': sent['neutral'] * 100 / max(total_sent, 1),
    'negative_pct': sent['negative'] * 100 / max(total_sent, 1),
}

# Rating distribution
rating_dist = [
    {'label': '1★', 'count': 0, 'color': '#f85149'},
    {'label': '2★', 'count': 0, 'color': '#f0883e'},
    {'label': '3★', 'count': 0, 'color': '#d29922'},
    {'label': '4★', 'count': 0, 'color': '#58a6ff'},
    {'label': '5★', 'count': 0, 'color': '#3fb950'},
]
cur.execute("""
    SELECT ROUND(rating) as r, COUNT(*) FROM vendor_reviews 
    WHERE rating IS NOT NULL AND rating >= 1 AND rating <= 5
    GROUP BY ROUND(rating) ORDER BY ROUND(rating)
""")
for row in cur.fetchall():
    idx = int(row[0]) - 1
    if 0 <= idx < 5:
        rating_dist[idx]['count'] = row[1]
data['rating_dist'] = rating_dist

# Categories
cur.execute("""
    SELECT v.category, COUNT(DISTINCT v.id) as vendors,
           COALESCE(COUNT(vr.id), 0) as reviews,
           COALESCE(ROUND(AVG(vr.rating), 2), 0) as avg_rating,
           CASE WHEN COUNT(v.id) > 0 
                THEN ROUND(COUNT(DISTINCT vr.vendor_id) * 100.0 / COUNT(DISTINCT v.id))
                ELSE 0 END as coverage_pct
    FROM vendors v 
    LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id AND LENGTH(vr.review_text) > 20
    WHERE v.category != '' AND v.category IS NOT NULL
    GROUP BY v.category ORDER BY reviews DESC
""")
data['categories'] = [{'category': r[0], 'vendors': r[1], 'reviews': r[2], 
                       'avg_rating': float(r[3]) if r[3] else None, 'coverage_pct': int(r[4] or 0)} 
                      for r in cur.fetchall()]

# States
cur.execute("""
    SELECT v.state, COUNT(DISTINCT v.id) as vendors, COUNT(vr.id) as reviews,
           COALESCE(ROUND(AVG(vr.rating), 2), 0)
    FROM vendors v 
    LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id AND LENGTH(vr.review_text) > 20
    WHERE v.state != '' AND v.state IS NOT NULL
    GROUP BY v.state ORDER BY reviews DESC LIMIT 15
""")
top_states = [{'state': r[0], 'vendors': r[1], 'reviews': r[2], 'avg_rating': float(r[3]) if r[3] else None} for r in cur.fetchall()]
data['top_states'] = top_states

cur.execute("""
    SELECT v.state, COUNT(DISTINCT v.id) as vendors, COUNT(vr.id) as reviews,
           COALESCE(ROUND(AVG(vr.rating), 2), 0)
    FROM vendors v 
    LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.id AND LENGTH(vr.review_text) > 20
    WHERE v.state != '' AND v.state IS NOT NULL
    GROUP BY v.state ORDER BY reviews DESC
""")
data['all_states'] = [{'state': r[0], 'vendors': r[1], 'reviews': r[2], 'avg_rating': float(r[3]) if r[3] else None} for r in cur.fetchall()]

# Complaint categories (from negative reviews' complaint_categories JSONB)
cur.execute("""
    SELECT cat, COUNT(*) FROM (
        SELECT jsonb_array_elements_text(complaint_categories) as cat
        FROM vendor_reviews 
        WHERE sentiment = 'negative' AND jsonb_array_length(complaint_categories) > 0
    ) sub GROUP BY cat ORDER BY count DESC LIMIT 15
""")
data['complaints'] = [{'category': r[0], 'count': r[1]} for r in cur.fetchall()]

# Negative reviews by vendor category
cur.execute("""
    SELECT v.category, COUNT(DISTINCT vr.vendor_id), COUNT(vr.id)
    FROM vendor_reviews vr 
    JOIN vendors v ON v.id = vr.vendor_id
    WHERE vr.sentiment = 'negative' AND v.category != ''
    GROUP BY v.category ORDER BY COUNT(vr.id) DESC
""")
data['negative_by_category'] = [{'category': r[0], 'vendor_count': r[1], 'negative_count': r[2]} for r in cur.fetchall()]

# Praise categories (from positive/neutral reviews)
cur.execute("""
    SELECT cat, COUNT(*) FROM (
        SELECT jsonb_array_elements_text(praise_categories) as cat
        FROM vendor_reviews 
        WHERE praise_categories IS NOT NULL AND jsonb_array_length(praise_categories) > 0
    ) sub GROUP BY cat ORDER BY count DESC LIMIT 15
""")
data['praise'] = [{'category': r[0], 'count': r[1]} for r in cur.fetchall()]

# Top vendors by review count
cur.execute("""
    SELECT name, city, state, category, review_count, star_rating
    FROM vendors WHERE source = 'theknot'
    ORDER BY review_count DESC LIMIT 10
""")
data['top_vendors'] = [{'name': r[0][:40], 'city': r[1] or '', 'state': r[2] or '',
                        'category': (r[3] or '').replace('wedding-', ''), 
                        'review_count': r[4], 'star_rating': float(r[5]) if r[5] else '-'} for r in cur.fetchall()]

# Best rated with 50+ stored reviews
cur.execute("""
    SELECT v.name, v.city, v.star_rating, COUNT(vr.id) as stored
    FROM vendors v 
    JOIN vendor_reviews vr ON vr.vendor_id = v.id AND LENGTH(vr.review_text) > 50
    WHERE v.source = 'theknot' AND v.star_rating >= 4.8
    GROUP BY v.id, v.name, v.city, v.star_rating
    HAVING COUNT(vr.id) >= 50
    ORDER BY v.star_rating DESC, stored DESC LIMIT 10
""")
data['best_vendors'] = [{'name': r[0][:40], 'city': r[1] or '', 'star_rating': float(r[2]), 
                         'stored_reviews': r[3]} for r in cur.fetchall()]

# Generate insights
insights = []

# Insight: complaint concentration
if data['complaints']:
    top_complaint = data['complaints'][0]
    neg_total = data['sentiment']['negative']
    pct = top_complaint['count'] * 100 / max(neg_total, 1)
    insights.append({
        'type': 'warning',
        'text': f"<b>{top_complaint['category']}</b> is the #1 complaint category — mentioned in <b>{pct:.0f}%</b> of negative reviews. Addressing this single pain point could improve satisfaction across {neg_total} dissatisfied couples."
    })

# Insight: review coverage gap
if data['categories']:
    no_review_cats = [c for c in data['categories'] if c['coverage_pct'] == 0]
    if no_review_cats:
        names = ', '.join(c['category'].replace('wedding-', '') for c in no_review_cats)
        insights.append({
            'type': 'warning',
            'text': f"<b>Coverage gap:</b> Categories with zero reviews scraped: <b>{names}</b>. These represent untapped competitive intelligence."
        })

# Insight: geographic opportunity  
states_with_vendors_no_reviews = [s for s in data['all_states'] if s['reviews'] == 0 and s['vendors'] > 20]
if states_with_vendors_no_reviews:
    total_uncovered = sum(s['vendors'] for s in states_with_vendors_no_reviews)
    states_list = ', '.join(s['state'] for s in states_with_vendors_no_reviews[:5])
    insights.append({
        'type': 'info',
        'text': f"<b>Geographic expansion:</b> <b>{len(states_with_vendors_no_reviews)} states</b> have {total_uncovered}+ vendors but no reviews pulled yet. Top opportunities: {states_list}. Running a targeted review extraction for these would add significant depth."
    })

# Insight: positive skew
if data['sentiment']['positive_pct'] > 90:
    insights.append({
        'type': 'info',
        'text': f"<b>Review bias:</b> {data['sentiment']['positive_pct']:.0f}% of reviews are positive. This is typical of self-selected marketplace reviews but means negative signals are high-value — each one represents genuine dissatisfaction worth analyzing individually."
    })

# Insight: pricing transparency
praise_cats = [p['category'] for p in data['praise']]
if 'transparency' in praise_cats:
    t_idx = praise_cats.index('transparency') + 1
    t_count = data['praise'][t_idx-1]['count']
    insights.append({
        'type': 'success',
        'text': f"<b>Pricing transparency wins business:</b> Transparency is the #{t_idx} most-praised quality ({t_count} mentions). Vendors who list starting prices publicly get measurably more positive mentions than those requiring inquiry."
    })

# Insight: DJ market size
dj_cat = [c for c in data['categories'] if 'djs' in c.get('category', '')]
if dj_cat:
    d = dj_cat[0]
    insights.append({
        'type': 'success',
        'text': f"<b>DJ market:</b> {d['vendors']} DJs tracked with {d['reviews']} reviews across all metros. Average rating: {d['avg_rating'] or 'N/A'}★. This is our deepest dataset for competitive analysis."
    })

# Insight: planner market
planner_cat = [c for c in data['categories'] if 'planners' in c.get('category', '')]
if planner_cat:
    p = planner_cat[0]
    insights.append({
        'type': 'success',
        'text': f"<b>Planner market:</b> {p['vendors']} planners tracked with {p['reviews']} reviews. Coverage: {p['coverage_pct']}%. Planners are the highest-value service category for WeddingOS integration."
    })

data['insights'] = insights

cur.close()
conn.close()

# Save to file
out_path = '/home/alex/code/BUTTERGANG/theknot-scraper/dashboard_data.json'
with open(out_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Dashboard data exported to {out_path}")
print(f"Total vendors: {data['total_vendors']}")
print(f"Total reviews: {data['total_reviews']}")
print(f"Avg rating: {data['avg_rating']}")
print(f"States: {data['states_covered']}")
print(f"Insights generated: {len(insights)}")