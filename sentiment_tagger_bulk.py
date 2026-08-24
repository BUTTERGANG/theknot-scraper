"""
Bulk sentiment tagging for 30K+ reviews — optimized with batch DB writes
Rule-based v1: keyword matching + rating signal
"""
import json, os, sys, re, time
from pathlib import Path

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2
from psycopg2.extras import execute_batch

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

POSITIVE_WORDS = set([
    'amazing', 'excellent', 'fantastic', 'wonderful', 'incredible', 'perfect', 'awesome',
    'great', 'best', 'loved', 'love', 'recommend', 'highly', 'beautiful',
    'professional', 'smooth', 'seamless', 'happy', 'delighted', 'thrilled', 'phenomenal',
    'outstanding', 'exceptional', 'impressive', 'fabulous', 'gorgeous', 'stunning',
    'flawless', 'superb', 'terrific', 'pleased', 'fun', 'energetic', 'talented',
])

NEGATIVE_WORDS = set([
    'terrible', 'awful', 'horrible', 'disappointed', 'disappointing', 'worst',
    'bad', 'poor', 'rude', 'unprofessional', 'late', 'no-show', 'no show',
    'never showed', 'cancelled', 'canceled', 'frustrating', 'annoyed', 'angry',
    'upset', 'waste of money', 'overpriced', 'uncommunicative', "didn't show",
    'did not show', 'problem', 'issues', 'issue', 'error', 'mistake', 'refund',
    'complaint', 'unhappy', 'regret', 'scam', 'unreliable', 'avoid', 'pushy',
    'dismissive', 'condescending', 'hidden fees', 'extra charge', 'surprise fee',
])

CATEGORY_KEYWORDS = {
    'communication': ['response', 'respon', 'email', 'message', 'text', 'call back', 'communicat', 'replied'],
    'responsiveness': ['quick', 'fast reply', 'prompt', 'slow to respond', 'waited days', 'took forever to'],
    'punctuality': ['on time', 'early', 'late', 'punctual', 'showed up on', 'arrived on', 'timely'],
    'reliability': ['reliable', 'dependable', 'sure thing', 'cancelled', 'no-show', 'no show', 'backed out', 'flaked'],
    'price': ['price', 'cost', 'expensive', 'affordable', 'overpriced', 'pricing', 'budget', '$'],
    'value': ['worth every penny', 'worth it', 'value', 'bang for', 'fair price', 'money well spent'],
    'transparency': ['hidden', 'fee', 'extra charge', 'transparent', 'upfront', 'no surprises'],
    'quality': ['quality', 'amazing photos', 'beautiful video', 'excellent sound', 'crisp', 'clear', 'stunning images'],
    'professionalism': ['professional', 'polite', 'courteous', 'respectful', 'accommodating', 'friendly', 'nice', 'kind'],
    'attitude': ['attitude', 'rude', 'dismissive', 'condescending', 'annoying', 'pushy', 'arrogant', 'snobby'],
    'setup': ['setup', 'set up', 'set-up', 'arrival', 'setup time', 'took down', 'breakdown', 'equipment setup'],
    'equipment': ['equipment', 'gear', 'sound system', 'speaker', 'lighting', 'photobooth', 'booth', 'camera gear', 'dj booth'],
    'logistics': ['logistics', 'organized', 'coordinated', 'smooth process', 'seamless', 'went smoothly', 'timeline management'],
    'timeline': ['timeline', 'schedule', 'on schedule', 'behind schedule', 'delayed', 'ran late', 'kept everything moving'],
    'planning': ['plan', 'planned', 'prepared', 'organized', 'walked us through', 'meeting', 'consultation', 'planning session'],
    'coordination': ['coordinated', 'worked with other vendors', 'venue staff', 'kept everything running', 'managed the flow'],
    'contract': ['contract', 'agreement', 'signed', 'fine print', 'terms', 'policy', 'deposit'],
    'billing': ['billing', 'invoice', 'payment', 'charged extra', 'paid in full', 'refund'],
    'guest_interaction': ['guests loved', 'crowd', 'dance floor was packed', 'everyone dancing', 'engaged the crowd', 'mc skills', 'emcee', 'read the room'],
    'extras': ['extra', 'add-on', 'included at no charge', 'bonus', 'free upgrade', 'complimentary'],
    'upselling': ['upsell', 'pushed upgrade', 'tried to sell', 'hard sell', 'constant upsell'],
    'cancellation': ['cancel', 'canceled', 'cancelled our booking', 'refund policy'],
    'technical': ['broke down', 'not working', 'glitch', 'malfunction', 'audio issue', 'sound cut out', 'camera failed', 'photobooth jammed'],
    'delivery': ['delivered ahead of schedule', 'photos came back', 'video was ready', 'final product', 'turnaround time', 'got our photos'],
    'experience': ['experience', 'best day ever', 'dream wedding', 'made our day special', 'unforgettable', 'memorable'],
    'recommendation': ['highly recommend', 'would recommend', 'book them again', 'hire them', 'worth every penny'],
}


def classify(text, rating):
    """Classify a single review"""
    text_lower = (text or '').lower()
    
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    
    # Rating-based signal (strongest)
    r_signal = 0
    if rating is not None:
        if rating >= 4.5: r_signal = 3
        elif rating >= 4.0: r_signal = 2
        elif rating >= 3.0: r_signal = 0
        elif rating >= 1.0 and rating < 2.0: r_signal = -3
        elif rating >= 2.0 and rating < 3.0: r_signal = -2
    
    total = r_signal + pos - neg
    
    if total > 0:
        sentiment = 'positive'
        confidence = min(0.99, 0.6 + 0.05 * min(8, pos + abs(r_signal)))
    elif total < 0:
        sentiment = 'negative'
        confidence = min(0.99, 0.6 + 0.05 * min(8, neg + abs(r_signal)))
    else:
        sentiment = 'neutral'
        confidence = 0.5
    
    return sentiment, round(confidence, 2)


def detect_categories(text):
    text_lower = (text or '').lower()
    matched = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(cat)
                break
    return matched


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    # Get unanalyzed reviews
    cur.execute("""
        SELECT id, review_text, rating FROM vendor_reviews 
        WHERE sentiment IS NULL OR sentiment = ''
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"Unanalyzed reviews: {len(rows)}")
    
    if not rows:
        print("All reviews already tagged!")
        cur.close(); conn.close()
        return
    
    start_time = time.time()
    
    # Process in batches of 1000
    batch_size = 1000
    stats = {'positive': 0, 'negative': 0, 'neutral': 0}
    cat_counts = {}
    processed = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        
        updates = []
        for rid, text, rating in batch:
            sentiment, confidence = classify(text, rating)
            cats = detect_categories(text)
            
            complaints = [c for c in cats if c not in ('experience', 'recommendation')] if sentiment == 'negative' else []
            praises = cats if sentiment != 'negative' else []
            
            updates.append((sentiment, confidence, json.dumps(complaints), json.dumps(praises), rid))
            stats[sentiment] += 1
            for c in cats:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        
        # Batch update
        execute_batch(cur, """
            UPDATE vendor_reviews SET 
                sentiment = %s,
                sentiment_confidence = %s::numeric,
                complaint_categories = %s::jsonb,
                praise_categories = %s::jsonb,
                analyzed_at = NOW(),
                analysis_model = 'heuristic-rulebased-v1'
            WHERE id = %s
        """, updates, page_size=500)
        
        conn.commit()
        processed += len(batch)
        
        elapsed = time.time() - start_time
        rate = processed / max(elapsed, 1)
        remaining = (len(rows) - processed) / max(rate, 0.01)
        pct = processed * 100 // len(rows)
        print(f"  [{processed}/{len(rows)}] ({pct}%) | {rate:.0f}/sec | ~{remaining/60:.0f}min remaining")
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"SENTIMENT TAGGING COMPLETE")
    print(f"{'='*60}")
    print(f"Time: {elapsed:.0f}s ({elapsed/max(processed,1)*1000:.1f}ms per review)")
    print(f"\nSentiment distribution:")
    for s in ['positive', 'neutral', 'negative']:
        count = stats.get(s, 0)
        pct = count * 100 // max(1, len(rows))
        bar = '#' * (pct // 2)
        print(f"  {s:10s}: {count:6d} ({pct:2d}%) {bar}")
    
    print(f"\nTop categories mentioned:")
    for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {k:25s}: {v}")
    
    # Verify in DB
    cur.execute("SELECT sentiment, COUNT(*) FROM vendor_reviews GROUP BY sentiment ORDER BY COUNT(*) DESC")
    print(f"\nDB verification:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()