"""
Unified database writer for wedding vendor scrapers
"""
import json
import psycopg2
from psycopg2.extras import Json, execute_values
from datetime import datetime

DB = {
    'host': 'localhost',
    'port': 54329,
    'user': 'postgres',
    'password': 'devpass',
    'dbname': 'wedding_vendors',
}


def get_conn():
    return psycopg2.connect(**DB)


def start_run(source, category, city='', state=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scrape_runs (source, category, city, state, started_at, status) "
        "VALUES (%s, %s, %s, %s, NOW(), 'running') RETURNING id",
        (source, category, city, state)
    )
    run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return run_id


def finish_run(run_id, found, successful, notes=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE scrape_runs SET completed_at = NOW(), vendors_found = %s, "
        "vendors_successful = %s, status = 'completed', notes = %s WHERE id = %s",
        (found, successful, notes, run_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def upsert_vendor(vendor_dict, run_id):
    """
    Upsert a vendor from any source.
    
    TheKnot keys: marketplace_id, vendor_id, name, phone, email, website_url,
        starting_price_min, starting_price_avg, starting_price_range,
        review_count, star_rating, description, headline,
        ad_tier, vendor_tier, service_area, city, state,
        facebook_url, instagram_username, pinterest_username,
        awards (list), deals (list), year_founded, team_size, travel_distance,
        theknot_url, scrape_success
    
    Zola keys: vendor_id, name, slug, phone, website_url, email,
        city, state, price_tier, starting_price, description,
        review_count, star_rating, categories, images, source_url
    
    WeddingWire keys: name, biz_id, biz_url, rating, review_count,
        starting_price, location, phone, website, description,
        category, badges, source_url
    """
    v = vendor_dict
    source = v.get('source', '')
    
    # Map source-specific ID to source_vendor_id
    if source == 'theknot':
        svid = v.get('vendor_id', '') or v.get('marketplace_id', '')
    elif source == 'zola':
        svid = v.get('vendor_id', '') or v.get('slug', '') or v.get('name', '')
    elif source == 'weddingwire':
        svid = v.get('biz_id', '') or v.get('name', '')
    else:
        svid = v.get('vendor_id', '') or v.get('name', '')
    
    # Parse pricing
    price_min = None
    price_avg = None
    
    # TheKnot has min/avg as cents
    if v.get('starting_price_min'):
        try:
            price_min = float(v['starting_price_min'])
        except: pass
    if v.get('starting_price_avg'):
        try:
            price_avg = float(v['starting_price_avg'])
        except: pass
    
    # Zola has starting_price as string like "$2400"
    sp = v.get('starting_price', '')
    if sp and not price_min:
        try:
            price_min = float(sp.replace('$', '').replace(',', '').replace('.00', ''))
        except: pass
    
    # Awards
    awards = v.get('awards', [])
    if isinstance(awards, list) and awards and isinstance(awards[0], str):
        awards = [{'name': a} for a in awards]
    
    # Deals
    deals = v.get('deals', [])
    
    # Build source URL
    source_url = v.get('theknot_url', '') or v.get('source_url', '') or v.get('biz_url', '') or ''
    
    # Category
    cat = v.get('category', '') or 'wedding-photographers'
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO vendors (
                source, source_vendor_id, source_url,
                name, category, city, state,
                phone, email, website_url,
                starting_price_min, starting_price_avg, starting_price_range, price_tier,
                star_rating, review_count,
                description, headline,
                ad_tier, vendor_tier, service_area,
                year_founded, team_size, travel_distance,
                facebook_url, instagram_username, pinterest_username,
                awards, deals,
                theknot_display_id, ww_biz_id, zola_slug,
                last_seen, scrape_run_id, raw_data
            ) VALUES (
                %(source)s, %(svid)s, %(source_url)s,
                %(name)s, %(cat)s, %(city)s, %(state)s,
                %(phone)s, %(email)s, %(website)s,
                %(price_min)s, %(price_avg)s, %(price_range)s, %(price_tier)s,
                %(rating)s, %(review_count)s,
                %(description)s, %(headline)s,
                %(ad_tier)s, %(vendor_tier)s, %(service_area)s,
                %(year_founded)s, %(team_size)s, %(travel_distance)s,
                %(facebook_url)s, %(instagram)s, %(pinterest)s,
                %(awards)s::jsonb, %(deals)s::jsonb,
                %(tk_id)s, %(ww_id)s, %(zola_slug)s,
                NOW(), %(run_id)s, %(raw)s::jsonb
            )
            ON CONFLICT (source, source_vendor_id) DO UPDATE SET
                name = EXCLUDED.name,
                phone = COALESCE(EXCLUDED.phone, vendors.phone),
                email = COALESCE(EXCLUDED.email, vendors.email),
                website_url = COALESCE(EXCLUDED.website_url, vendors.website_url),
                starting_price_min = COALESCE(EXCLUDED.starting_price_min, vendors.starting_price_min),
                starting_price_avg = COALESCE(EXCLUDED.starting_price_avg, vendors.starting_price_avg),
                star_rating = EXCLUDED.star_rating,
                review_count = EXCLUDED.review_count,
                description = COALESCE(EXCLUDED.description, vendors.description),
                awards = EXCLUDED.awards,
                deals = EXCLUDED.deals,
                last_seen = NOW(),
                scrape_run_id = EXCLUDED.scrape_run_id,
                raw_data = EXCLUDED.raw_data
        """, {
            'source': source, 'svid': svid, 'source_url': source_url,
            'name': v.get('name', ''), 'cat': cat,
            'city': v.get('address_city', '') or v.get('city', '') or '',
            'state': v.get('address_state', '') or v.get('state', '') or '',
            'phone': v.get('phone', '') or '',
            'email': v.get('email', '') or '',
            'website': v.get('website_url', '') or v.get('display_website_url', '') or v.get('website', '') or '',
            'price_min': price_min,
            'price_avg': price_avg,
            'price_range': v.get('starting_price_range', '') or '',
            'price_tier': str(v.get('price_tier', '') or ''),
            'rating': float(v.get('star_rating', 0) or v.get('rating', 0) or 0),
            'review_count': int(v.get('review_count', 0) or v.get('reviewsCount', 0) or 0),
            'description': (v.get('description', '') or '')[:5000],
            'headline': v.get('headline', '') or '',
            'ad_tier': v.get('ad_tier', '') or '',
            'vendor_tier': v.get('vendor_tier', '') or '',
            'service_area': v.get('service_area', '') or '',
            'year_founded': v.get('year_founded'),
            'team_size': v.get('team_size'),
            'travel_distance': v.get('travel_distance'),
            'facebook_url': v.get('facebook_url', '') or '',
            'instagram': v.get('instagram_username', '') or '',
            'pinterest': v.get('pinterest_username', '') or '',
            'awards': json.dumps(awards),
            'deals': json.dumps(deals),
            'tk_id': v.get('displayId', '') or v.get('theknot_display_id', '') or '',
            'ww_id': v.get('biz_id', '') or '',
            'zola_slug': v.get('slug', '') or v.get('zola_slug', '') or '',
            'run_id': run_id,
            'raw': json.dumps(v, default=str)[:10000],
        })
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  DB error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def get_stats():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT source, COUNT(*) FROM vendors GROUP BY source ORDER BY source")
    by_source = dict(cur.fetchall())
    
    cur.execute("SELECT COUNT(*) FROM vendors")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT source, COUNT(*) FROM vendors WHERE phone != '' GROUP BY source")
    with_phone = dict(cur.fetchall())
    
    cur.execute("SELECT source, COUNT(*) FROM vendors WHERE email != '' GROUP BY source")
    with_email = dict(cur.fetchall())
    
    cur.execute("SELECT source, COUNT(*) FROM vendors WHERE starting_price_min IS NOT NULL GROUP BY source")
    with_pricing = dict(cur.fetchall())
    
    cur.close()
    conn.close()
    
    return {
        'total': total,
        'by_source': by_source,
        'with_phone': with_phone,
        'with_email': with_email,
        'with_pricing': with_pricing,
    }