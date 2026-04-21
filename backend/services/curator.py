"""
Curator — Dainik-Vidya
Generates Top 20 internally (sliced to user preference client-side).
Now uses the unified AI service (Groq → Gemini → OpenRouter → fallback).
Strict output validation: valid JSON, required fields, URL integrity.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from utils.timezone import now_ist

from database import get_collection
from core.logger import get_logger
from services.ai_service import curate_with_ai

logger = get_logger()

REQUIRED_FIELDS = {"rank", "title", "url", "summary", "importance_score"}


# ── Candidate loader ──────────────────────────────────────────────────────────

async def _load_candidate_articles(limit: int = 80) -> List[dict]:
    """Load recent processed articles as curation candidates."""
    news_col = get_collection("news")
    since = datetime.now(timezone.utc) - timedelta(hours=36)

    cursor = news_col.find(
        {"processed": True, "scraped_at": {"$gte": since}}
    ).sort("importance_score", -1).limit(limit)
    articles = await cursor.to_list(length=limit)

    # Fall back to unprocessed if not enough processed
    if len(articles) < 10:
        cursor = news_col.find({}).sort("scraped_at", -1).limit(limit)
        articles = await cursor.to_list(length=limit)

    return articles


# ── Internal mock/fallback ────────────────────────────────────────────────────

def _mock_items(articles: List[dict], n: int) -> List[dict]:
    """Rank by importance_score + recency — no AI required."""
    scored = sorted(
        articles,
        key=lambda a: (
            -(a.get("importance_score") or 5),
            -(a.get("scraped_at").timestamp()
              if hasattr(a.get("scraped_at"), "timestamp") else 0),
        ),
    )
    return [
        {
            "rank": i + 1,
            "title": a.get("title", ""),
            "ai_title": a.get("ai_title") or a.get("title", ""),
            "summary": (
                a.get("ai_summary") or a.get("summary")
                or "Full article available at source."
            ),
            "importance_reason": f"Top story from {a.get('source', 'a major news source')}.",
            "source": a.get("source", ""),
            "url": a.get("url", ""),
            "category": a.get("category", "general"),
            "keywords": a.get("keywords", []),
            "importance_score": a.get("importance_score") or 5,
            "ai_used": False,
        }
        for i, a in enumerate(scored[:n])
        if a.get("url")   # NEVER include items without a URL
    ]


# ── Output validation ─────────────────────────────────────────────────────────

def _validate_curated_items(items: list, original_articles: List[dict]) -> List[dict]:
    """Strict validation of AI output. Discards invalid items."""
    validated = []
    for item in items:
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            logger.warning(
                f"Curator item missing fields {missing}, discarding: "
                f"{item.get('title', '?')}"
            )
            continue

        if not item.get("url"):
            logger.warning(
                f"Curator item has no URL, discarding: {item.get('title', '?')}"
            )
            continue

        item["importance_score"] = item.get("importance_score") or 5
        if not item.get("ai_title"):
            item["ai_title"] = item.get("title", "")
        if not isinstance(item.get("keywords"), list):
            item["keywords"] = []

        item["ai_used"] = True
        validated.append(item)

    return validated


# ── Main curation entry point ─────────────────────────────────────────────────

async def curate_top10() -> Dict:
    """
    Generate Top-20 for the curated_top10 collection, per language.
    Uses the unified AI service (Groq → Gemini → OpenRouter → fallback).
    Client-side slices to user preference (5/10/20).
    Never crashes pipeline.
    """
    today = now_ist().date().isoformat()
    top10_col = get_collection("top10")
    articles = await _load_candidate_articles(200)

    if not articles:
        logger.warning("Curator: no candidate articles found")
        return {}

    from collections import defaultdict
    articles_by_lang: dict = defaultdict(list)
    for art in articles:
        lang = art.get("language", "en")
        articles_by_lang[lang].append(art)

    n = 20   # Always generate top 20 internally
    results: Dict = {}

    for lang, lang_articles in articles_by_lang.items():
        logger.info(
            f"Curating Top {n} for lang={lang} | candidates={len(lang_articles)}"
        )
        try:
            # ── Call unified AI service ───────────────────────────────────────
            ai_items = await curate_with_ai(
                lang_articles, n=n, language=lang
            )

            if ai_items:
                validated = _validate_curated_items(ai_items, lang_articles)
                if len(validated) >= 3:
                    items = validated
                    logger.info(
                        f"✅ Curator AI SUCCESS | lang={lang} items={len(items)}"
                    )
                else:
                    logger.warning(
                        f"Only {len(validated)} valid items from AI curator "
                        f"→ mock fallback | lang={lang}"
                    )
                    items = _mock_items(lang_articles, n)
            else:
                logger.warning(
                    f"Curator AI returned nothing → mock fallback | lang={lang}"
                )
                items = _mock_items(lang_articles, n)

        except Exception as _ce:
            logger.warning(
                f"Curator unexpected exception for lang={lang}: {_ce} → fallback"
            )
            items = _mock_items(lang_articles, n)

        doc = {
            "date": today,
            "language": lang,
            "items": items,
            "generated_at": datetime.now(timezone.utc),
        }
        await top10_col.update_one(
            {"date": today, "language": lang},
            {"$set": doc},
            upsert=True,
        )
        results[lang] = doc
        logger.info(f"Top {len(items)} curated | date={today} lang={lang}")

    return results