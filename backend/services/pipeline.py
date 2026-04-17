"""
Pipeline orchestrator — Dainik-Vidya

Full hybrid pipeline:
  1. RSS scrape          → up to MAX_SCRAPER_ARTICLES new articles
  2. NewsAPI fetch       → up to MAX_NEWS_API_ARTICLES new articles
  3. Title deduplication → remove near-duplicate articles
  4. Category ranking    → priority sort + sports cap
  5. AI processing       → only top MAX_AI_ARTICLES sent to Gemini
  6. Curation            → Top 5 highlights
  7. Trends              → daily analytics
  8. Meta update         → record lastFetchedAt timestamp
  9. Email digest        → send to subscribers

Triggered by: /fetch-news endpoint (also /trigger-pipeline alias) and scheduler.
Clean summary log emitted at the end of every run.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

# ─── Priority constants ───────────────────────────────────────────────────────
CATEGORY_PRIORITY: Dict[str, int] = {
    "politics":      1,
    "geopolitics":   2,
    "business":      3,
    "finance":       4,
    "technology":    5,
    "health":        6,
    "science":       7,
    "world":         8,
    "india":         9,
    "general":       10,
    "entertainment": 11,
    "sports":        12,
}

SPORTS_CATEGORIES = {"sports"}
MAX_SPORTS_PCT   = 0.12    # cap ESPN/sport at 12 % of total articles
TITLE_SIM_THRESHOLD = 0.55  # Jaccard threshold for title deduplication

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
    "as", "by", "its", "he", "she", "they", "we", "you", "this", "that",
    "are", "from", "after", "amid", "over", "new", "say", "says",
})


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _words(title: str) -> frozenset:
    return frozenset(
        w.lower().strip(".,!?\"':-()[]")
        for w in title.split()
        if len(w) > 3 and w.lower() not in _STOP_WORDS and w.isalpha()
    )


def _jaccard(t1: str, t2: str) -> float:
    s1, s2 = _words(t1), _words(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


# ─── Step 3: Deduplication ───────────────────────────────────────────────────
async def deduplicate_recent(lookback_hours: int = 24) -> Dict[str, int]:
    """
    Remove title-similar duplicates from articles ingested in the last
    `lookback_hours` hours. URL duplicates are already prevented at insert time.
    Returns {"removed": N}.
    """
    collection = get_collection("news")
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    cursor = collection.find(
        {"scraped_at": {"$gte": since}},
        {"_id": 1, "title": 1, "scraped_at": 1, "importance_score": 1},
    ).sort("scraped_at", 1)   # oldest first → oldest survives
    articles = await cursor.to_list(length=2000)

    to_delete = []
    survivors: List[Tuple[str, str]] = []   # (id_str, title)

    for art in articles:
        title = art.get("title", "")
        dup = False
        for _, surv_title in survivors:
            if _jaccard(title, surv_title) >= TITLE_SIM_THRESHOLD:
                dup = True
                break
        if dup:
            to_delete.append(art["_id"])
        else:
            survivors.append((str(art["_id"]), title))

    if to_delete:
        from bson import ObjectId
        result = await collection.delete_many({"_id": {"$in": to_delete}})
        removed = result.deleted_count
    else:
        removed = 0

    return {"removed": removed, "survived": len(survivors)}


# ─── Step 4: Ranking ─────────────────────────────────────────────────────────
def _rank_key(doc: dict) -> tuple:
    priority = CATEGORY_PRIORITY.get(doc.get("category", "general"), 10)
    pub = doc.get("published_at")
    ts = -pub.timestamp() if hasattr(pub, "timestamp") else 0
    return (priority, ts)


async def get_ranked_unprocessed(limit: int = None) -> List[dict]:
    """
    Fetch unprocessed articles from the last 24h, apply priority sort +
    sports cap, return top `limit` (default: settings.max_ai_articles).
    """
    collection = get_collection("news")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    cursor = collection.find(
        {"processed": False, "scraped_at": {"$gte": since}}
    ).sort("published_at", -1).limit(300)
    pool = await cursor.to_list(length=300)

    # Sports cap
    non_sports = [a for a in pool if a.get("category") not in SPORTS_CATEGORIES]
    sports     = [a for a in pool if a.get("category") in SPORTS_CATEGORIES]
    max_sports = max(1, int(len(pool) * MAX_SPORTS_PCT))
    combined   = non_sports + sports[:max_sports]

    ranked = sorted(combined, key=_rank_key)
    n = limit or settings.max_ai_articles
    return ranked[:n]


# ─── Step 5 proxy: route to ai_processor ────────────────────────────────────
async def ai_process_ranked(ranked_articles: List[dict]) -> Dict[str, int]:
    from services.ai_processor import process_articles
    return await process_articles(ranked_articles)


# ─── Main orchestrator ───────────────────────────────────────────────────────
async def run_full_pipeline() -> Dict:
    """
    Execute the complete hybrid pipeline and return a clean summary log.
    Called by the scheduler (7 AM + 2 PM IST) and the /trigger-pipeline endpoint.
    """
    run_start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("🚀 Dainik-Vidya Pipeline — START")
    logger.info("=" * 60)

    summary = {
        "scraped": 0,
        "news_api": 0,
        "merged_total": 0,
        "deduplicated_removed": 0,
        "ai_processed": 0,
        "ai_failed": 0,
        "errors": [],
    }

    # ── Step 1: RSS scrape ────────────────────────────────────────
    try:
        logger.info("📡 [1/6] RSS scraping...")
        from services.scraper import scrape_all_feeds
        rss = await scrape_all_feeds()
        summary["scraped"] = rss.get("new_articles", 0)
        logger.info(f"     RSS: +{summary['scraped']} new articles")
    except Exception as e:
        logger.error(f"     RSS scrape failed: {e}")
        summary["errors"].append(f"rss: {e}")

    # ── Step 2: NewsAPI fetch ─────────────────────────────────────
    try:
        logger.info("🌐 [2/6] NewsAPI fetch...")
        from services.news_api import fetch_news_api
        api = await fetch_news_api()
        summary["news_api"] = api.get("new", 0)
        logger.info(f"     NewsAPI: +{summary['news_api']} new articles")
    except Exception as e:
        logger.error(f"     NewsAPI fetch failed: {e}")
        summary["errors"].append(f"newsapi: {e}")

    summary["merged_total"] = summary["scraped"] + summary["news_api"]

    # ── Step 3: Deduplication ─────────────────────────────────────
    try:
        logger.info("🔍 [3/6] Deduplicating by title similarity...")
        dedup = await deduplicate_recent(lookback_hours=24)
        summary["deduplicated_removed"] = dedup.get("removed", 0)
        logger.info(f"     Removed {dedup['removed']} duplicates — {dedup['survived']} unique articles")
    except Exception as e:
        logger.error(f"     Dedup failed: {e}")
        summary["errors"].append(f"dedup: {e}")

    # ── Step 4+5: Rank + AI process ───────────────────────────────
    try:
        logger.info(f"🤖 [4/6] Ranking + Gemini AI (top {settings.max_ai_articles})...")
        ranked = await get_ranked_unprocessed(settings.max_ai_articles)
        logger.info(f"     Selected {len(ranked)} articles for AI processing")
        ai = await ai_process_ranked(ranked)
        summary["ai_processed"] = ai.get("processed", 0)
        summary["ai_failed"] = ai.get("errors", 0)
        logger.info(f"     AI done: ✅ {ai.get('processed', 0)}  ❌ {ai.get('errors', 0)}")
    except Exception as e:
        logger.error(f"     AI processing failed: {e}")
        summary["errors"].append(f"ai: {e}")

    # ── Step 6: Curate ────────────────────────────────────────────
    try:
        logger.info("⭐ [5/6] Curating Top 10 highlights...")
        from services.curator import curate_top10
        await curate_top10()
    except Exception as e:
        logger.error(f"     Curation failed: {e}")
        summary["errors"].append(f"curator: {e}")

    # ── Step 7: Trends ────────────────────────────────────────────
    try:
        logger.info("📊 [6/7] Computing trends...")
        from services.trends_service import compute_trends
        await compute_trends()
    except Exception as e:
        logger.error(f"     Trends failed: {e}")
        summary["errors"].append(f"trends: {e}")

    # ── Step 8: Update fetch metadata ─────────────────────────────
    try:
        logger.info("🕒 [7/7] Updating fetch metadata...")
        from routes.meta import update_last_fetched
        await update_last_fetched()
    except Exception as e:
        logger.warning(f"     Meta update failed (non-fatal): {e}")

    # ── Step 9: Email ─────────────────────────────────────────────
    try:
        from services.email_service import send_daily_digest
        await send_daily_digest()
    except Exception as e:
        logger.warning(f"     Email digest failed (non-fatal): {e}")

    elapsed = round((datetime.now(timezone.utc) - run_start).total_seconds())
    summary["elapsed_seconds"] = elapsed

    logger.info("=" * 60)
    logger.info(f"✅ Pipeline complete ({elapsed}s)")
    logger.info(
        f"   scraped={summary['scraped']} "
        f"news_api={summary['news_api']} "
        f"merged={summary['merged_total']} "
        f"dedup_removed={summary['deduplicated_removed']} "
        f"ai_processed={summary['ai_processed']} "
        f"failed={summary['ai_failed']}"
    )
    if summary["errors"]:
        logger.warning(f"   Errors: {summary['errors']}")
    logger.info("=" * 60)

    return summary
