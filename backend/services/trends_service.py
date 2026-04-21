"""
Trends analysis — Dainik-Vidya
Computes category counts, keyword frequency, and AI insights per language.
AI calls delegated to the unified ai_service (Groq → Gemini → OpenRouter → fallback).
"""
from datetime import datetime, timezone
from typing import Dict, List
from collections import Counter, defaultdict

from database import get_collection
from core.logger import get_logger
from services.ai_service import generate_trends_with_ai
from utils.timezone import now_ist, get_today_range_ist, ist_to_utc

logger = get_logger()

STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "with", "has", "have", "been", "were", "was", "will", "that", "this",
    "from", "by", "as", "are", "its", "it", "not", "be", "more", "new", "says",
    "said", "after", "over", "into", "about", "than", "up", "what", "how", "he",
    "she", "they", "his", "her", "their", "also", "year", "first", "two", "one",
}


async def compute_trends() -> Dict:
    """Compute category + keyword trends, and AI insights per language."""
    news_col = get_collection("news")
    trends_col = get_collection("trends")
    today = now_ist().date().isoformat()

    start_ist, _ = get_today_range_ist()
    from_date = ist_to_utc(start_ist)

    cursor = news_col.find({"scraped_at": {"$gte": from_date}})
    all_articles = await cursor.to_list(length=2000)

    if not all_articles:
        logger.warning(f"No articles found for {today} trends computation.")
        return {}

    articles_by_lang: dict = defaultdict(list)
    for art in all_articles:
        lang = art.get("language", "en")
        articles_by_lang[lang].append(art)

    results: Dict = {}

    for lang, articles in articles_by_lang.items():
        category_counts: Counter = Counter()
        all_keywords: list = []

        for art in articles:
            category_counts[art.get("category", "general")] += 1

            for kw in art.get("keywords", []):
                word = kw.lower().strip()
                if word and word not in STOP_WORDS and word.isalpha():
                    all_keywords.append(word)

            for w in art.get("title", "").split():
                w = w.lower().strip(".,!?\"'()")
                if len(w) > 4 and w not in STOP_WORDS and w.isalpha():
                    all_keywords.append(w)

        kw_freq = Counter(all_keywords)
        trending_keywords = [
            {"word": w, "count": c} for w, c in kw_freq.most_common(25)
        ]
        most_covered = (
            category_counts.most_common(1)[0][0] if category_counts else "N/A"
        )

        # ── AI trends via unified service ─────────────────────────────────────
        ai_data = await generate_trends_with_ai(articles, language=lang)

        doc = {
            "date": today,
            "language": lang,
            "category_counts": dict(category_counts),
            "trending_keywords": trending_keywords,
            "most_covered": most_covered,
            "total_articles": len(articles),
            "computed_at": datetime.now(timezone.utc),
            "overview": ai_data["overview"],
            "top_themes": ai_data["top_themes"],
            "category_insights": ai_data["category_insights"],
            "ai_used": ai_data.get("ai_used", False),
            "ai_provider": ai_data.get("provider", "fallback"),
        }
        await trends_col.update_one(
            {"date": today, "language": lang},
            {"$set": doc},
            upsert=True,
        )
        results[lang] = doc
        logger.info(
            f"Trends computed | date={today} lang={lang} "
            f"articles={len(articles)} ai_used={doc['ai_used']} "
            f"provider={doc['ai_provider']}"
        )

    return results
