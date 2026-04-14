"""
AI Processor — Dainik-Vidya
Uses Google Gemini Flash to generate summaries, category tags,
importance scores, and keywords for top-ranked articles ONLY.

Optimisations:
  • Only processes the N articles passed in (pre-ranked by pipeline)
  • Skips already-processed articles (cache)
  • Semaphore-based concurrency cap (max 4 parallel Gemini calls)
  • Retry with back-off (max 2 retries per article)
  • Rate-limit delay between calls
  • Clean summary log — no per-article Gemini noise
"""
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

# ── Gemini setup ──────────────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    _gemini_ok = True
except ImportError:
    _gemini_ok = False
    logger.warning("google-generativeai not installed — running in mock mode")

MOCK_MODE = not settings.gemini_api_key or not _gemini_ok

if not MOCK_MODE:
    genai.configure(api_key=settings.gemini_api_key)
    _model = genai.GenerativeModel(
        model_name=settings.gemini_model,       # default: "gemini-1.5-flash"
        generation_config=genai.types.GenerationConfig(
            temperature=0.25,
            max_output_tokens=350,
        ),
    )

# Semaphore: max 4 concurrent Gemini calls to stay within RPM
_SEM = asyncio.Semaphore(4)
# Delay between each call (seconds) to stay within free-tier RPM
_CALL_DELAY = 60.0 / settings.gemini_rpm

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
})

SYSTEM_PROMPT = """\
You are a concise, professional news editor. Analyse the article snippet and return ONLY a valid JSON object:
{
  "ai_title": "<clean, engaging headline, max 15 words>",
  "summary": "<2-3 sentence factual summary>",
  "category": "<one of: politics|geopolitics|business|finance|technology|health|science|world|india|sports|entertainment|general>",
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>", "<keyword4>"],
  "importance_score": <integer 1-10 reflecting global significance>
}
Return ONLY the JSON. No markdown fences, no extra text."""


# ── Internal helpers ──────────────────────────────────────────────────────────
async def _call_gemini(article: dict) -> Optional[dict]:
    """Single Gemini call, wrapped in semaphore + delay."""
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Category hint: {article.get('category', '')}\n"
        f"Snippet: {(article.get('summary') or '')[:400]}"
    )
    try:
        async with _SEM:
            response = await asyncio.to_thread(_model.generate_content, prompt)
            await asyncio.sleep(_CALL_DELAY)   # throttle within semaphore slot

        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None
    except Exception:
        return None


async def _call_with_retry(article: dict, max_retries: int = 2) -> Optional[dict]:
    """Retry Gemini call up to max_retries times with exponential back-off."""
    for attempt in range(max_retries + 1):
        result = await _call_gemini(article)
        if result is not None:
            return result
        if attempt < max_retries:
            await asyncio.sleep(2.0 ** attempt * 3)   # 3s, 6s
    return None


def _mock_process(article: dict) -> dict:
    """Mock result when no API key or in dev mode."""
    title = article.get("title", "")
    words = [
        w.lower().strip(".,!?\"'")
        for w in title.split()
        if len(w) > 3 and w.lower() not in _STOP_WORDS and w.isalpha()
    ]
    return {
        "ai_title": title,
        "summary": article.get("summary") or f"Full article available at {article.get('source', 'the source')}.",
        "category": article.get("category", "general"),
        "keywords": list(set(words))[:6],
        "importance_score": 5,
    }


# ── Public interface ──────────────────────────────────────────────────────────
async def process_articles(articles: List[dict]) -> Dict[str, int]:
    """
    Process a pre-selected list of articles (from pipeline.get_ranked_unprocessed).
    Skips any that are already processed (cache).
    Returns {"processed": N, "errors": M, "skipped_cached": K}.
    """
    collection = get_collection("news")
    stats = {"processed": 0, "errors": 0, "skipped_cached": 0}

    if not articles:
        return stats

    # Filter out already-processed (cache hit)
    unprocessed = [a for a in articles if not a.get("processed")]
    stats["skipped_cached"] = len(articles) - len(unprocessed)

    if not unprocessed:
        return stats

    logger.info(f"  Gemini processing {len(unprocessed)} articles (mock={MOCK_MODE})")

    async def _handle(article: dict):
        try:
            if MOCK_MODE:
                result = _mock_process(article)
            else:
                result = await _call_with_retry(article) or _mock_process(article)

            await collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "ai_title":        result.get("ai_title", article.get("title")),
                    "ai_summary":      result.get("summary", ""),
                    "category":        result.get("category", article.get("category", "general")),
                    "keywords":        result.get("keywords", []),
                    "importance_score": result.get("importance_score", 5),
                    "processed":       True,
                    "processed_at":    datetime.now(timezone.utc),
                }},
            )
            stats["processed"] += 1
        except Exception as e:
            logger.debug(f"  Article processing error ({article.get('_id')}): {e}")
            stats["errors"] += 1

    # Run all article handlers concurrently (Semaphore limits actual API calls)
    await asyncio.gather(*[_handle(a) for a in unprocessed])
    return stats


# Backward-compat shim — previously called by the old scheduler directly
async def process_all_unprocessed() -> Dict[str, int]:
    """
    Legacy entry: process up to MAX_AI_ARTICLES from recent unprocessed pool.
    Prefer calling via pipeline.run_full_pipeline().
    """
    from services.pipeline import get_ranked_unprocessed
    ranked = await get_ranked_unprocessed(settings.max_ai_articles)
    return await process_articles(ranked)