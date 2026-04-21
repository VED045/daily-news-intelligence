"""
AI Processor — Dainik-Vidya (v3.0)
Processes only the top MAX_AI_ARTICLES ranked articles per pipeline run.
Delegates ALL AI calls to the unified ai_service (Groq → Gemini → OpenRouter → fallback).

Key rules:
  • Called only for the top 10-15 ranked articles — NOT every scraped article
  • Skips articles already processed (cache check on `processed` flag)
  • Never crashes pipeline on any AI failure
  • Logs provider used per batch
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List

from database import get_collection
from config import settings
from core.logger import get_logger
from services.ai_service import generate_ai_output_batch

logger = get_logger()

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
})


# ── Internal mock (when all AI providers fail for a specific article) ─────────

def _mock_process(article: dict) -> dict:
    """Deterministic fallback when all AI providers fail."""
    title = article.get("title", "")
    words = list({
        w.lower().strip(".,!?\"'")
        for w in title.split()
        if len(w) > 3 and w.lower() not in _STOP_WORDS and w.isalpha()
    })
    return {
        "ai_title":        title,
        "summary":         (
            article.get("summary")
            or f"Full article at {article.get('source', 'source')}."
        ),
        "category":        article.get("category", "general"),
        "keywords":        words[:5],
        "importance_score": 5,
    }


# ── Public interface ──────────────────────────────────────────────────────────

async def process_articles(articles: List[dict]) -> Dict[str, int]:
    """
    Process a pre-ranked list of articles through the AI provider waterfall.

    Only the top MAX_AI_ARTICLES are ever passed here from pipeline.py.
    Skips already-processed articles (processed=True acts as a cache).
    Never crashes on any AI failure.
    """
    collection = get_collection("news")
    stats = {
        "processed": 0,
        "errors": 0,
        "skipped_cached": 0,
        "mock": 0,
        "gemini_success": 0,    # kept for pipeline summary compat
        "gemini_fallback": 0,
    }

    # ── Cache gate: skip already-processed articles ───────────────────────────
    unprocessed = [a for a in articles if not a.get("processed")]
    stats["skipped_cached"] = len(articles) - len(unprocessed)
    if not unprocessed:
        logger.info("AI processor: all articles already processed — nothing to do")
        return stats

    logger.info(
        f"AI processing started | count={len(unprocessed)} "
        f"(skipped_cached={stats['skipped_cached']})"
    )

    # ── Call unified AI service (batched) ─────────────────────────────────────
    try:
        batch_results = await generate_ai_output_batch(unprocessed, mode="curation")
    except Exception as e:
        logger.error(f"AI batch call failed entirely: {e} — using mock for all")
        batch_results = []

    # Build index → result map (1-based index from AI service)
    result_map: Dict[int, dict] = {}
    for item in batch_results:
        idx = item.get("index")
        if idx is not None:
            result_map[idx] = item

    # ── Apply results back to MongoDB ─────────────────────────────────────────
    async def _save(i: int, article: dict):
        try:
            result = result_map.get(i + 1)   # 1-based
            ai_used = result is not None

            if not ai_used:
                result = _mock_process(article)
                stats["mock"] += 1
                stats["gemini_fallback"] += 1
                logger.debug(
                    f"Mock fallback used | title='{article.get('title','')[:50]}'"
                )
            else:
                stats["gemini_success"] += 1
                logger.debug(
                    f"AI result applied | title='{article.get('title','')[:50]}'"
                )

            await collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "ai_title":         result.get("ai_title", article.get("title")),
                    "ai_summary":       result.get("summary", ""),
                    "category":         result.get("category", article.get("category", "general")),
                    "keywords":         result.get("keywords", []),
                    "importance_score": result.get("importance_score", 5),
                    "ai_used":          ai_used,
                    "processed":        True,
                    "processed_at":     datetime.now(timezone.utc),
                }},
            )
            stats["processed"] += 1
        except Exception as e:
            logger.exception(f"Article save error | article_id={article.get('_id')}")
            stats["errors"] += 1

    await asyncio.gather(*[_save(i, a) for i, a in enumerate(unprocessed)])

    logger.info(
        f"AI processing done | processed={stats['processed']} "
        f"ai_hits={stats['gemini_success']} fallback={stats['gemini_fallback']} "
        f"errors={stats['errors']}"
    )
    return stats


# Backward-compat shim
async def process_all_unprocessed() -> Dict[str, int]:
    from services.pipeline import get_ranked_unprocessed
    ranked = await get_ranked_unprocessed(settings.max_ai_articles)
    return await process_articles(ranked)