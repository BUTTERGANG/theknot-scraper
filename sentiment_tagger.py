"""
Sentiment tagging pipeline — tag wedding vendor reviews by complaint/praise category

Uses an LLM to classify each review into sentiment + specific complaint/praise categories.
Queries the reviews stored in the DB, tags them, updates the vendor_reviews table.

Categories for wedding vendors (DJs, planners, photobooths):
- communication / responsiveness
- punctuality / reliability
- price / value / transparency
- quality of work / final product
- professionalism / attitude
- setup / equipment / logistics
- timeline / planning / coordination
- contract / billing / hidden fees
- crowds / guest interaction
- extras / add-ons / upselling
- cancellation / no-show / tech issues
- overall recommendation
"""
import json, os, sys, re, time
from pathlib import Path

sys.path.insert(0, '/home/alex/code/BUTTERGANG/theknot-scraper')
import psycopg2

DB = {'host': 'localhost', 'port': 54329, 'user': 'postgres', 'password': 'devpass', 'dbname': 'wedding_vendors'}

# Compensation categories
COMPLAINT_CATEGORIES = [
    "communication", "responsiveness", "punctuality", "reliability", "price",
    "value", "transparency", "quality", "professionalism", "attitude",
    "setup", "equipment", "logistics", "timeline", "planning", "coordination",
    "contract", "billing", "hidden_fees", "guest_interaction", "extras",
    "upselling", "cancellation", "no_show", "technical", "delivery",
]

PRAISE_CATEGORIES = [
    "communication", "responsiveness", "punctuality", "reliability", "price",
    "value", "transparency", "quality", "professionalism", "attitude",
    "setup", "equipment", "logistics", "timeline", "planning", "coordination",
    "contract", "billing", "guest_interaction", "extras", "experience",
    "recommendation",
]


def get_unanalyzed_reviews(limit=500):
    """Get reviews that haven't been sentiment-tagged yet"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT vr.id, vr.review_text, vr.rating, v.name as vendor_name, vr.source
        FROM vendor_reviews vr
        JOIN vendors v ON v.id = vr.vendor_id
        WHERE vr.sentiment = '' OR vr.sentiment IS NULL
        ORDER BY vr.scraped_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'id': r[0], 'text': r[1], 'rating': r[2], 'vendor': r[3], 'source': r[4]} for r in rows]


def update_review(review_id, sentiment, confidence, complaint_cats, praise_cats):
    """Update a review with sentiment analysis results"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE vendor_reviews SET
                sentiment = %s,
                sentiment_confidence = %s,
                complaint_categories = %s::jsonb,
                praise_categories = %s::jsonb,
                analyzed_at = NOW(),
                analysis_model = 'heuristic-rulebased-v1'
            WHERE id = %s
        """, (sentiment, confidence, json.dumps(complaint_cats), json.dumps(praise_cats), review_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"    DB error: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


# ─── RULE-BASED SENTIMENT + CATEGORY DETECTION ─────────────────

# Keywords mapping to categories
CATEGORY_KEYWORDS = {
    'communication': ['response', 'respon', 'email', 'message', 'text', 'call', 'communicat', 'replied', 'follow up', 'reach out', 'contact'],
    'responsiveness': ['response', 'quick', 'fast reply', 'respon', 'prompt', 'slow to', 'waited', 'took long', 'took forever'],
    'punctuality': ['on time', 'on-time', 'early', 'late', 'punctual', 'showed up', 'arrived', 'was there', 'timely'],
    'reliability': ['reliable', 'depend', 'sure thing', 'cancelled', 'no-show', 'no show', 'backed out', 'flaked', 'showed up'],
    'price': ['price', 'cost', 'expensive', 'afford', 'overpriced', 'underpriced', 'dollar', 'pricing', 'budget', '$'],
    'value': ['worth', 'value', 'bang for', 'great deal', 'fair price', 'worth it', 'money'],
    'transparency': ['hidden', 'fee', 'extra charge', 'surprise', 'transparent', 'upfront', 'quote', 'estimate'],
    'quality': ['quality', 'great', 'amazing', 'beautiful', 'excellent', 'wonderful', 'perfect', 'professional', 'top notch', 'high quality', 'gorgeous', 'stunning'],
    'professionalism': ['professional', 'polite', 'courteous', 'respectful', 'accommodat', 'friendly', 'nice', 'kind', 'pleasant', 'personable'],
    'attitude': ['attitude', 'rude', 'unprofessional', 'dismissive', 'condescend', 'annoying', 'pushy', 'arrogant', 'snobby'],
    'setup': ['setup', 'set up', 'set-up', 'setup equipment', 'arrival', 'setup time', 'took down', 'equipment setup'],
    'equipment': ['equipment', 'gear', 'camera', 'sound', 'speaker', 'lighting', 'machine', 'photobooth', 'booth', 'table', 'tent', 'decor'],
    'logistics': ['logistic', 'organiz', 'coordinat', 'smooth', 'seamless', 'went smoothly', 'timeline', 'schedule', 'update'],
    'timeline': ['timeline', 'schedule', 'on schedule', 'behind schedule', 'on time', 'delayed', 'early'],
    'planning': ['plan', 'planned', 'prepared', 'organized', 'started', 'walked through', 'meeting', 'consultation', 'planning'],
    'coordination': ['coordinat', 'worked with', 'team', 'other vendor', 'vendor', 'venue staff', 'kept everything', 'managed'],
    'contract': ['contract', 'agreement', 'sign', 'fine print', 'terms', 'policy'],
    'billing': ['bill', 'invoice', 'payment', 'deposit', 'charged', 'charge', 'paid', 'refund'],
    'hidden_fees': ['hidden', 'extra fee', 'additional charge', 'surprise fee', 'tax', 'gratuity', 'service charge'],
    'guest_interaction': ['guest', 'crowd', 'audience', 'party', 'dance floor', 'mc', 'emcee', 'announce', 'interact', 'everyone'],
    'extras': ['extra', 'add-on', 'add on', 'upgrade', 'included', 'bonus', 'free'],
    'upselling': ['upsell', 'push', 'upgrade', 'price increase', 'tried to sell', 'hard sell'],
    'cancellation': ['cancel', 'canceled', 'cancelled', 'refund', 'no-show', 'no show'],
    'no_show': ['no-show', 'no show', 'never showed', 'didn\'t show', 'did not show', 'stood us up'],
    'technical': ['mirror', 'broken', 'not working', 'broke', 'glitch', 'malfunction', 'bug', 'audio', 'camera failed'],
    'delivery': ['delivered', 'delivery', 'on time', 'finished', 'complete', 'completed', 'final product', 'photos', 'album', 'video'],
    'experience': ['experience', 'amazing experience', 'fantastic', 'incredible', 'best', 'awesome', 'loved', 'enjoyed', 'fun'],
    'recommendation': ['recommend', 'would use', 'hire them', 'highly', 'book them', 'worth every'],
}

# Strong positive/negative indicators
POSITIVE_WORDS = [
    'amazing', 'excellent', 'fantastic', 'wonderful', 'incredible', 'perfect', 'awesome',
    'great', 'best', 'loved', 'love', 'recommend', 'highly', 'beautiful', 'wonderful',
    'professional', 'smooth', 'seamless', 'happy', 'delighted', 'thrilled', 'phenomenal',
    'outstanding', 'exceptional', 'impressive', 'fabulous', 'gorgeous', 'stunning',
    'flawless', 'superb', 'terrific', 'exceptional', 'praise', 'pleased',
]

NEGATIVE_WORDS = [
    'terrible', 'awful', 'horrible', 'disappointed', 'disappointing', 'disappointment',
    'worst', 'bad', 'poor', 'rude', 'unprofessional', 'late', 'no-show', 'no show',
    'never showed', 'cancelled', 'canceled', 'frustrating', 'annoyed', 'angry', 'upset',
    'waste of money', 'overpriced', 'uncommunicative', 'didn\'t show', 'problem',
    'issues', 'issue', 'error', 'mistake', 'refund', 'complaint', 'unhappy', 'regret',
    'scam', 'unreliable', 'unprofessional', 'shockingly', 'avoid',
]


def detect_categories(text, keyword_map):
    """Detect which categories a review mentions by keyword analysis"""
    text_lower = text.lower()
    matched = set()
    for cat, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                matched.add(cat)
                break
    return sorted(matched)


def classify_sentiment(text, rating):
    """Classify sentiment: positive/neutral/negative based on rating + text"""
    text_lower = text.lower()
    
    pos_hits = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_hits = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    
    # Rating-based signal (most reliable for weddings)
    rating_signal = 0
    if rating and rating >= 4.5: rating_signal = 2
    elif rating and rating >= 4.0: rating_signal = 1
    elif rating and rating <= 2.0: rating_signal = -2
    elif rating and rating <= 3.0: rating_signal = -1
    
    total = rating_signal + (pos_hits - neg_hits)
    
    if total >= 1:
        return 'positive', min(0.99, 0.5 + 0.15 * (pos_hits + abs(rating_signal)))
    elif total <= -1:
        return 'negative', min(0.99, 0.5 + 0.15 * (neg_hits + abs(rating_signal)))
    else:
        return 'neutral', 0.5


def tag_review(review):
    """Tag a single review with sentiment + categories"""
    text = review['text']
    rating = review['rating']
    
    sentiment, confidence = classify_sentiment(text, rating)
    
    # Complaints = negative/neutral sentiment mentions, filtered
    # For negative reviews, find the categories they complain about
    if sentiment == 'negative':
        # Emphasis on negative categories
        complaint_keywords = {k: v for k, v in CATEGORY_KEYWORDS.items()}
        complaints = detect_categories(text, complaint_keywords)
        # Remove categories that are purely positive
        praises = []
    elif sentiment == 'positive':
        complaints = []
        praise_keywords = CATEGORY_KEYWORDS
        praises = detect_categories(text, praise_keywords)
    else:  # neutral
        complaints = detect_categories(text, CATEGORY_KEYWORDS)
        praises = []
    
    # Refine: for the specific complaint/praise points, we need text spans.
    # For now, just store the top categories.
    return sentiment, confidence, complaints, praises


def main():
    reviews = get_unanalyzed_reviews(500)
    print(f"Found {len(reviews)} unanalyzed reviews")
    
    stats = {'positive': 0, 'negative': 0, 'neutral': 0}
    cat_counts = {}
    
    for i, review in enumerate(reviews):
        sentiment, confidence, complaints, praises = tag_review(review)
        
        ok = update_review(
            review['id'], sentiment, confidence, complaints, praises
        )
        
        stats[sentiment] = stats.get(sentiment, 0) + 1
        for c in complaints + praises:
            cat_counts[c] = cat_counts.get(c, 0) + 1
        
        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(reviews)}")
    
    print(f"\n=== SENTIMENT DISTRIBUTION ===")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} ({v*100//max(1,len(reviews))}%)")
    
    print(f"\n=== TOP CATEGORIES ===")
    for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {k}: {v}")
    
    print(f"\n✅ Sentiment tagging complete")


if __name__ == '__main__':
    main()