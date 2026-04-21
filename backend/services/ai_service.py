"""
Unified AI Service — Dainik-Vidya
Multi-provider fallback: Groq → Gemini → OpenRouter → internal fallback.

Provider priority (based on rate limits and reliability):
  1. Groq          — llama-3.3-70b-versatile   (highest free rate limit)
  2. Gemini        — gemini-2.5-flash           (high quality, Google)
  3. OpenRouter    — mistralai/mistral-7b-instruct (safety net)
  4. Internal      — deterministic keyword/summary fallback (never crashes)

Key features:
  • Batching: 10–15 articles per AI call (vs 1 call/article previously)
  • Caching: skips articles that already have ai_summary
  • Rate-limit detection: 429/quota errors skip provider immediately
  • Observable: clear per-provider logs + global usage counter
  • Never raises — always returns a result list

Usage:
    from services.ai_service import generate_ai_output_batch, get_provider_usage
    results = await generate_ai_output_batch(articles, mode="curation")
"""
import json
import asyncio
import re
from typing import Dict, List, Optional

import httpx

from config import settings
from core.logger import get_logger

logger = get_logger()

# ── Global provider usage tracker (reset per pipeline run via reset_provider_usage) ──
provider_usage: Dict[str, int] = {"groq": 0, "gemini": 0, "openrouter": 0, "fallback": 0}


def reset_provider_usage() -> None:
    """Reset usage counters — call once at pipeline start."""
    for k in provider_usage:
        provider_usage[k] = 0


def get_provider_usage() -> Dict[str, int]:
    return dict(provider_usage)


# ── Stop-words for internal keyword extraction ────────────────────────────────
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
    "that", "this", "from", "by", "as", "are", "its", "it", "not", "be",
    "more", "new", "says", "said", "after", "over", "into", "about", "he",
    "she", "they", "his", "her", "their", "also", "year", "first", "two",
})

BATCH_SIZE = 12   # articles per AI call


# ── Prompt templates ──────────────────────────────────────────────────────────

def _build_batch_prompt(batch: List[dict], mode: str) -> str:
    """Build a single prompt that covers a batch of articles."""
    numbered = "\n\n".join(
        f"{i + 1}. Title: {a.get('title', 'Untitled')}\n"
        f"   Source: {a.get('source', 'Unknown')}\n"
        f"   Category: {a.get('category', 'general')}\n"
        f"   Snippet: {(a.get('content_preview') or a.get('summary') or '')[:300]}"
        for i, a in enumerate(batch)
    )

    if mode == "curation":
        instruction = (
            "You are a senior news editor. For EACH article below, return a JSON array.\n"
            "Each element must have:\n"
            '  "index": <1-based integer matching the article number>,\n'
            '  "ai_title": "<compelling headline, max 15 words>",\n'
            '  "summary": "<2-3 sentence factual summary>",\n'
            '  "keywords": ["kw1", "kw2", "kw3"],\n'
            '  "importance_score": <integer 1-10>,\n'
            '  "category": "<politics|geopolitics|business|finance|technology|'
            'health|science|world|india|sports|entertainment|general>"\n\n'
            "Return ONLY a valid JSON array. No markdown fences, no extra text."
        )
    elif mode == "trends":
        instruction = (
            "You are a news analyst. Summarise today's news batch.\n"
            "Return ONLY a single JSON object with:\n"
            '  "overview": "<4-6 sentence summary of major events>",\n'
            '  "top_themes": ["<theme 1>", "<theme 2>", "<theme 3>"],\n'
            '  "category_insights": {"<category>": "<1 sentence>"}\n\n'
            "No markdown fences, no extra text."
        )
    else:  # summary (fallback mode)
        instruction = (
            "Analyse each article and return a JSON array.\n"
            "Each element: {\"index\": <1-based>, \"ai_title\": \"...\", "
            "\"summary\": \"...\", \"keywords\": [...]}\n"
            "Return ONLY the JSON array."
        )

    return f"{instruction}\n\nArticles:\n{numbered}"


def _build_curator_prompt(articles: List[dict], n: int, language: str,
                           topic_instruction: str = "") -> str:
    """Build the full curation prompt for curator.py (article list → ranked top-N)."""
    article_list = "\n".join(
        f"{i + 1}. [{a.get('source')}] {a.get('title')} "
        f"(cat={a.get('category')}, score={a.get('importance_score') or 5}) URL:{a.get('url')}"
        for i, a in enumerate(articles[:60])
    )
    return (
        f"You are a senior international news editor curating today's most important stories.\n"
        f"Target Language: {language}\n"
        f"Select the {n} most globally significant stories from the list.\n"
        f"Prioritise: geopolitics, elections, economic crises, major world events.\n"
        f"De-prioritise: celebrity, minor local sports.\n"
        f"{topic_instruction}\n"
        f"CRITICAL RULES:\n"
        f"1. Return the EXACT original article URL.\n"
        f"2. 'title' MUST be the EXACT original title.\n"
        f"3. 'ai_title' is your rewrite (max 15 words) in {language}.\n"
        f"4. Every item MUST have 'url' and 'importance_score' (integer 1-10).\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{ "top": [ {{ "rank": 1, "title": "...", "ai_title": "...", '
        f'"summary": "...", "importance_reason": "...", "source": "...", '
        f'"url": "...", "category": "...", "keywords": [...], "importance_score": 5 }} ] }}\n\n'
        f"Today's articles:\n{article_list}"
    )


def _build_trends_prompt(articles: List[dict], language: str) -> str:
    """Build the trends summary prompt."""
    sorted_arts = sorted(articles, key=lambda a: -(a.get("importance_score") or 5))[:40]
    art_text = "\n".join(
        f"- [{a.get('category', 'general')}] {a.get('title', '')}: "
        f"{(a.get('summary') or '')[:200]}"
        for a in sorted_arts
    )
    return (
        f"You are an expert news analyst. Target language: {language}.\n"
        f"Based on these articles generate:\n"
        f'  "overview": 4-6 sentence summary of major events today.\n'
        f'  "top_themes": list of 3-5 short theme phrases.\n'
        f'  "category_insights": dict of top categories with 1-sentence explanation.\n\n'
        f"Return ONLY valid JSON:\n"
        f'{{ "overview": "...", "top_themes": ["..."], '
        f'"category_insights": {{"finance": "..."}} }}\n\n'
        f"Today's articles:\n{art_text}"
    )


# ── JSON utility ─────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        inner = parts[1] if len(parts) >= 2 else parts[0]
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    return text


def _is_rate_limit_error(err: Exception) -> bool:
    """Detect 429 / quota / rate-limit in any exception."""
    msg = str(err).lower()
    return any(kw in msg for kw in ("429", "quota", "rate limit", "rate_limit",
                                     "too many requests", "resource_exhausted"))


# ── Internal fallback helpers ─────────────────────────────────────────────────

def _extract_keywords(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    seen: set = set()
    result = []
    for w in words:
        if len(w) > 4 and w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            result.append(w)
        if len(result) >= 5:
            break
    return result


def _basic_summary(text: str) -> str:
    """Return first ~150 chars of text as a basic summary."""
    text = (text or "").strip()
    if not text:
        return "Full article available at source."
    return text[:200] + ("…" if len(text) > 200 else "")


def _internal_fallback_batch(batch: List[dict]) -> List[dict]:
    """Deterministic fallback when all AI providers fail."""
    return [
        {
            "index": i + 1,
            "ai_title": a.get("title", "Untitled"),
            "summary": _basic_summary(a.get("summary") or a.get("content_preview") or ""),
            "keywords": _extract_keywords(a.get("title", "") + " " + (a.get("summary") or "")),
            "importance_score": a.get("importance_score") or 5,
            "category": a.get("category", "general"),
        }
        for i, a in enumerate(batch)
    ]


# ── Provider: Groq ────────────────────────────────────────────────────────────

async def _call_groq(prompt: str) -> str:
    """Call Groq API (OpenAI-compatible). Raises on any error."""
    if not settings.groq_api_key:
        raise RuntimeError("No GROQ_API_KEY configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        )
        if resp.status_code == 429:
            raise RuntimeError(f"429 rate limit: {resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Provider: Gemini ──────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> str:
    """Call Gemini via google-generativeai SDK. Raises on any error."""
    if not settings.gemini_api_key:
        raise RuntimeError("No GEMINI_API_KEY configured")

    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai not installed")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
    response = await asyncio.wait_for(
        asyncio.to_thread(model.generate_content, prompt),
        timeout=45.0,
    )
    return response.text


# ── Provider: OpenRouter ──────────────────────────────────────────────────────

async def _call_openrouter(prompt: str) -> str:
    """Call OpenRouter (OpenAI-compatible). Raises on any error."""
    if not settings.openrouter_api_key:
        raise RuntimeError("No OPENROUTER_API_KEY configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://dainik-vidya.app",
                "X-Title": "Dainik-Vidya",
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        )
        if resp.status_code == 429:
            raise RuntimeError(f"429 rate limit: {resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Core: single-prompt call with provider waterfall ─────────────────────────

async def _call_with_fallback(prompt: str, context: str = "") -> tuple[str, str]:
    """
    Try providers in order: Groq → Gemini → OpenRouter.
    Returns (raw_text, provider_name).
    Raises RuntimeError only if ALL providers fail — caller must handle that.
    """
    providers = [
        ("groq",        _call_groq),
        ("gemini",      _call_gemini),
        ("openrouter",  _call_openrouter),
    ]

    for name, fn in providers:
        try:
            text = await fn(prompt)
            provider_usage[name] += 1
            logger.info(
                f"{'🟢' if name == 'groq' else '🔵' if name == 'gemini' else '🟣'} "
                f"{name.upper()} USED | {context}"
            )
            return text, name
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning(f"⚠️ {name.upper()} RATE LIMITED — skipping | {e}")
            else:
                logger.warning(f"⚠️ {name.upper()} FAILED: {type(e).__name__}: {e}")

    raise RuntimeError("All AI providers exhausted")


# ── Public: batch processing for articles ────────────────────────────────────

async def generate_ai_output_batch(
    articles: List[dict],
    mode: str = "curation",
) -> List[dict]:
    """
    Batch-process a list of articles through the AI provider waterfall.

    Args:
        articles: list of article dicts (must have at least 'title')
        mode: "curation" | "trends" | "summary"

    Returns:
        List of result dicts with keys: index, ai_title, summary, keywords,
        importance_score, category.  Always returns one item per input article.
        Never raises.
    """
    # ── Cache check: skip articles that already have ai_summary ──────────────
    to_process = [a for a in articles if not a.get("ai_summary")]
    cached_count = len(articles) - len(to_process)
    if cached_count:
        logger.info(f"AI cache hit: {cached_count} articles skipped")

    if not to_process:
        logger.info("All articles cached — no AI calls needed")
        return []

    results: List[dict] = []

    # ── Process in batches ────────────────────────────────────────────────────
    for batch_start in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        logger.info(f"AI batch {batch_num} | size={len(batch)} mode={mode}")

        prompt = _build_batch_prompt(batch, mode)

        try:
            raw, provider = await _call_with_fallback(
                prompt, context=f"batch={len(batch)} mode={mode}"
            )
            text = _strip_fences(raw)

            # Parse JSON — expect a list for curation/summary, obj for trends
            parsed = json.loads(text)

            if isinstance(parsed, list):
                for item in parsed:
                    item.setdefault("index", len(results) + 1)
                results.extend(parsed)
            elif isinstance(parsed, dict) and "top" in parsed:
                # Curator-style — wrap each item with an index
                for i, item in enumerate(parsed["top"]):
                    item["index"] = batch_start + i + 1
                results.extend(parsed["top"])
            else:
                # trends-style single object — return as-is in a list wrapper
                parsed["index"] = batch_start + 1
                results.append(parsed)

        except json.JSONDecodeError as e:
            logger.warning(f"AI JSON parse failed for batch {batch_num}: {e} → fallback")
            provider_usage["fallback"] += 1
            results.extend(_internal_fallback_batch(batch))
        except RuntimeError:
            # All providers exhausted
            logger.error(f"❌ ALL PROVIDERS FAILED for batch {batch_num} → fallback used")
            provider_usage["fallback"] += 1
            results.extend(_internal_fallback_batch(batch))
        except Exception as e:
            logger.error(f"Unexpected error in AI batch {batch_num}: {e} → fallback")
            provider_usage["fallback"] += 1
            results.extend(_internal_fallback_batch(batch))

    logger.info(f"📊 Batch AI complete | total_results={len(results)}")
    return results


# ── Public: curation (returns curator-format top-N list) ─────────────────────

async def curate_with_ai(
    articles: List[dict],
    n: int,
    language: str = "en",
    topic_instruction: str = "",
) -> Optional[List[dict]]:
    """
    Ask AI to pick and rank the top-n stories from `articles`.
    Returns a validated list of curator-format dicts, or None if all providers fail.
    Curator.py calls this instead of its direct Gemini call.
    """
    prompt = _build_curator_prompt(articles, n, language, topic_instruction)
    logger.info(f"Curator AI request | lang={language} n={n} candidates={len(articles)}")

    try:
        raw, provider = await _call_with_fallback(
            prompt, context=f"curation lang={language} n={n}"
        )
        text = _strip_fences(raw)
        data = json.loads(text)
        items = data.get("top", []) if isinstance(data, dict) else data
        return items if isinstance(items, list) else None
    except json.JSONDecodeError as e:
        logger.warning(f"Curator AI JSON parse failed: {e}")
        return None
    except RuntimeError:
        logger.error("❌ ALL PROVIDERS FAILED for curation → mock fallback")
        return None
    except Exception as e:
        logger.error(f"Curator AI unexpected error: {e}")
        return None


# ── Public: trends summary ────────────────────────────────────────────────────

async def generate_trends_with_ai(
    articles: List[dict],
    language: str = "en",
) -> dict:
    """
    Generate AI-driven trends summary (overview, top_themes, category_insights).
    Always returns a dict — never raises.
    """
    _FALLBACK = {
        "overview": (
            "AI summary unavailable. Today featured standard news coverage "
            "across multiple sectors."
        ),
        "top_themes": ["General Headlines", "Varied News Coverage", "Daily Updates"],
        "category_insights": {"general": "A mix of standard daily news."},
        "ai_used": False,
        "provider": "fallback",
    }

    if not articles:
        return _FALLBACK

    prompt = _build_trends_prompt(articles, language)
    logger.info(f"Trends AI request | lang={language} articles={len(articles)}")

    try:
        raw, provider = await _call_with_fallback(
            prompt, context=f"trends lang={language}"
        )
        text = _strip_fences(raw)
        data = json.loads(text)
        logger.info(f"✅ Trends AI SUCCESS | provider={provider} lang={language}")
        return {
            "overview": data.get("overview", _FALLBACK["overview"]),
            "top_themes": data.get("top_themes", []),
            "category_insights": data.get("category_insights", {}),
            "ai_used": True,
            "provider": provider,
        }
    except json.JSONDecodeError as e:
        logger.warning(f"Trends AI JSON parse failed: {e} → fallback")
        return _FALLBACK
    except RuntimeError:
        logger.error("❌ ALL PROVIDERS FAILED for trends → fallback")
        return _FALLBACK
    except Exception as e:
        logger.error(f"Trends AI unexpected error: {e} → fallback")
        return _FALLBACK
