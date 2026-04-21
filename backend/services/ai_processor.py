"""
AI Processor — Dainik-Vidya (v2.1)
— Gemini 404 fix: runtime model probe + fallback
— Only processes top 10-15 ranked articles (passed from pipeline)
— Semaphore rate-limit, 2-retry backoff, cache skip
— Never crashes pipeline on Gemini failure
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database import get_collection
from config import settings
from core.logger import get_logger

logger = get_logger()

# ── Gemini initialisation ─────────────────────────────────────────────────────
_gemini_ok   = False
_model       = None
MOCK_MODE    = True
_ACTIVE_MODEL = None   # actual model name that worked

try:
    import google.generativeai as genai
    _gemini_ok = True
except ImportError:
    logger.warning("google-generativeai not installed — AI running in mock mode")

def _init_gemini():
    """
    Probe Gemini at startup:
      1. Configure API key
      2. List available models, log them
      3. Pick the first model that supports generateContent
      4. Fail gracefully → MOCK_MODE = True
    """
    global _model, MOCK_MODE, _ACTIVE_MODEL

    if not _gemini_ok or not settings.gemini_api_key:
        logger.warning("Gemini: no API key or SDK missing — mock mode active")
        MOCK_MODE = True
        return

    try:
        genai.configure(api_key=settings.gemini_api_key)

        # ── List available models ─────────────────────────────────
        try:
            available = [
                m.name for m in genai.list_models()
                if "generateContent" in (m.supported_generation_methods or [])
            ]
            logger.info(f"Gemini available models: {available}")
        except Exception as probe_err:
            logger.warning(f"Gemini: could not list models — {probe_err}")
            available = []

        # ── Model preference list ─────────────────────────────────
        candidates = [
            settings.gemini_model,       # env default: "gemini-1.5-flash"
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro",
            "gemini-pro",
        ]
        # If we got a model list, filter to only available ones (strip "models/" prefix)
        available_short = [m.replace("models/", "") for m in available]
        ordered = [c for c in candidates if not available_short or c in available_short]
        if not ordered:
            ordered = candidates   # fallback: try anyway

        last_err = None
        for candidate in ordered:
            try:
                m = genai.GenerativeModel(
                    model_name=candidate,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.25,
                        max_output_tokens=350,
                    ),
                )
                # Quick smoke test — list_models already validated, skip extra call
                _model        = m
                _ACTIVE_MODEL = candidate
                MOCK_MODE     = False
                logger.info(f"✅ Gemini model ready: {candidate}")
                return
            except Exception as e:
                last_err = e
                logger.debug(f"Gemini model '{candidate}' init failed: {e}")
                continue

        logger.exception("Gemini: all model candidates failed.")
        logger.warning("Falling back to mock AI mode — pipeline will continue without summaries")
        MOCK_MODE = True

    except Exception as e:
        logger.exception("Gemini init error — mock mode active")
        MOCK_MODE = True


# Run probe at import time
_init_gemini()

# ── Rate control ──────────────────────────────────────────────────────────────
_SEM        = asyncio.Semaphore(4)   # max 4 concurrent API calls
_CALL_DELAY = 60.0 / max(settings.gemini_rpm, 1)   # seconds between calls

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
})

SYSTEM_PROMPT = """\
You are a concise, professional news editor. Analyse the article and return ONLY valid JSON:
{
  "ai_title": "<clean, engaging headline, max 15 words>",
  "summary": "<2-3 sentence factual summary>",
  "category": "<one of: politics|geopolitics|business|finance|technology|health|science|world|india|sports|entertainment|general>",
  "keywords": ["kw1", "kw2", "kw3", "kw4"],
  "importance_score": <integer 1-10 reflecting global significance>
}
Return ONLY the JSON. No markdown fences, no extra text."""


# ── Internal helpers ──────────────────────────────────────────────────────────
async def _call_gemini(article: dict) -> Optional[dict]:
    """Single Gemini call, guarded by semaphore + delay. Returns None on any error."""
    if MOCK_MODE or _model is None:
        return None

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Category hint: {article.get('category', '')}\n"
        f"Snippet: {(article.get('content_preview') or article.get('summary') or '')[:500]}"
    )
    try:
        async with _SEM:
            response = await asyncio.wait_for(
                asyncio.to_thread(_model.generate_content, prompt),
                timeout=30.0,
            )
            await asyncio.sleep(_CALL_DELAY)

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text.strip())

    except asyncio.TimeoutError:
        logger.debug(f"Gemini timeout for: {article.get('title', '')[:50]}")
        return None
    except json.JSONDecodeError:
        logger.debug("Gemini: invalid JSON response")
        return None
    except Exception as e:
        # Suppress repetitive 404 / quota noise — log once at debug level
        logger.debug(f"Gemini call failed | error={type(e).__name__} details={e}")
        return None


async def _call_with_retry(article: dict, max_retries: int = 2) -> Optional[dict]:
    """Retry logic with exponential back-off. Returns None after all retries fail."""
    for attempt in range(max_retries + 1):
        result = await _call_gemini(article)
        if result is not None:
            return result
        if attempt < max_retries:
            wait = 3.0 * (2 ** attempt)   # 3s, 6s
            logger.debug(f"Gemini retry {attempt+1}/{max_retries} in {wait:.0f}s")
            await asyncio.sleep(wait)
    return None


def _mock_process(article: dict) -> dict:
    """Deterministic mock when Gemini is unavailable."""
    title = article.get("title", "")
    words = list({
        w.lower().strip(".,!?\"'")
        for w in title.split()
        if len(w) > 3 and w.lower() not in _STOP_WORDS and w.isalpha()
    })
    return {
        "ai_title":        title,
        "summary":         article.get("summary") or f"Full article at {article.get('source', 'source')}.",
        "category":        article.get("category", "general"),
        "keywords":        words[:5],
        "importance_score": 5,
    }


# ── Public interface ──────────────────────────────────────────────────────────
async def process_articles(articles: List[dict]) -> Dict[str, int]:
    """
    Process a pre-ranked list of articles.
    Skips already-processed ones (cache). Never crashes on Gemini failure.
    """
    collection = get_collection("news")
    stats = {"processed": 0, "errors": 0, "skipped_cached": 0, "mock": 0}

    unprocessed = [a for a in articles if not a.get("processed")]
    stats["skipped_cached"] = len(articles) - len(unprocessed)
    if not unprocessed:
        return stats

    logger.info(f"AI processing started | count={len(unprocessed)} model={_ACTIVE_MODEL or 'mock'} mock={MOCK_MODE}")

    async def _handle(article: dict):
        try:
            if MOCK_MODE:
                result = _mock_process(article)
                stats["mock"] += 1
                ai_used = False
            else:
                api_result = await _call_with_retry(article)
                if api_result:
                    logger.info("🤖 Gemini USED for curation")
                    result = api_result
                    ai_used = True
                else:
                    logger.warning("⚠️ Gemini FAILED — using fallback logic")
                    result = _mock_process(article)
                    stats["mock"] += 1
                    ai_used = False

            await collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "ai_title":        result.get("ai_title", article.get("title")),
                    "ai_summary":      result.get("summary", ""),
                    "category":        result.get("category", article.get("category", "general")),
                    "keywords":        result.get("keywords", []),
                    "importance_score": result.get("importance_score", 5),
                    "ai_used":         ai_used,
                    "processed":       True,
                    "processed_at":    datetime.now(timezone.utc),
                }},
            )
            stats["processed"] += 1
        except Exception as e:
            logger.exception(f"Article save error | article_id={article.get('_id')}")
            stats["errors"] += 1

    await asyncio.gather(*[_handle(a) for a in unprocessed])
    return stats


# Backward-compat shim
async def process_all_unprocessed() -> Dict[str, int]:
    from services.pipeline import get_ranked_unprocessed
    ranked = await get_ranked_unprocessed(settings.max_ai_articles)
    return await process_articles(ranked)