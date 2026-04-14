"""
Trends analysis: computes category counts, keyword frequency, daily snapshots.
"""
import logging
from datetime import datetime, date
from typing import Dict
from collections import Counter
from database import get_collection

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "with", "has", "have", "been", "were", "was", "will", "that", "this",
    "from", "by", "as", "are", "its", "it", "not", "be", "more", "new", "says",
    "said", "after", "over", "into", "about", "than", "up", "what", "how", "he",
    "she", "they", "his", "her", "their", "also", "year", "first", "two", "one",
}


async def compute_trends() -> Dict:
    """Compute category + keyword trends from today's articles."""
    news_col = get_collection("news")
    trends_col = get_collection("trends")
    today = date.today().isoformat()

    from_date = datetime.combine(date.today(), datetime.min.time())
    cursor = news_col.find({"scraped_at": {"$gte": from_date}})
    articles = await cursor.to_list(length=500)

    # Fallback to latest 200
    if not articles:
        cursor = news_col.find({}).sort("scraped_at", -1).limit(200)
        articles = await cursor.to_list(length=200)

    category_counts: Counter = Counter()
    all_keywords: list = []

    for art in articles:
        category_counts[art.get("category", "general")] += 1

        for kw in art.get("keywords", []):
            word = kw.lower().strip()
            if word and word not in STOP_WORDS and word.isalpha():
                all_keywords.append(word)

        # Extract meaningful words from title too
        for w in art.get("title", "").split():
            w = w.lower().strip(".,!?\"'()")
            if len(w) > 4 and w not in STOP_WORDS and w.isalpha():
                all_keywords.append(w)

    kw_freq = Counter(all_keywords)
    trending_keywords = [{"word": w, "count": c} for w, c in kw_freq.most_common(25)]
    most_covered = category_counts.most_common(1)[0][0] if category_counts else "N/A"

    doc = {
        "date": today,
        "category_counts": dict(category_counts),
        "trending_keywords": trending_keywords,
        "most_covered": most_covered,
        "total_articles": len(articles),
        "computed_at": datetime.utcnow(),
    }
    await trends_col.update_one({"date": today}, {"$set": doc}, upsert=True)
    logger.info(f"✅ Trends computed for {today}: {dict(category_counts)}")
    return doc
