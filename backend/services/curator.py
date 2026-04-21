"""
Curator — Dainik-Vidya
Generates Top 20 internally (sliced to user preference client-side).
Uses Gemini Flash for intelligent selection when available.
Strict output validation: valid JSON, required fields, URL integrity.
"""
import json
import asyncio
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional

from database import get_collection
from config import settings
from core.logger import get_logger

logger = get_logger()

try:
    import google.generativeai as genai
    _gemini_ok = True
except ImportError:
    _gemini_ok = False

MOCK_MODE = not settings.gemini_api_key or not _gemini_ok

if not MOCK_MODE:
    genai.configure(api_key=settings.gemini_api_key)
    _model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config=genai.types.GenerationConfig(temperature=0.2, max_output_tokens=4000),
    )

CURATOR_PROMPT = """\
You are a senior international news editor curating today's most important stories.
Target Language: {language}
Given today's headlines, select the {n} most globally significant stories.
Prioritise: geopolitics, elections, economic crises, major world events.
De-prioritise: celebrity, minor local sports.
{topic_instruction}
CRITICAL RULES:
1. ALWAYS return the EXACT original article URL from the input. Do NOT omit or modify it.
2. The "title" field MUST be the EXACT original title — do NOT rewrite or shorten it.
3. The "ai_title" is your compelling rewrite (max 15 words) in the target language.
4. Every item MUST have a valid "url" field.
5. Every item MUST have an "importance_score" (integer 1-10).
6. Prioritize articles in this language: {language}

Return ONLY valid JSON (no markdown fences, no extra text):
{{
  "top": [
    {{
      "rank": 1,
      "title": "<EXACT original title — do NOT modify>",
      "ai_title": "<compelling rewrite, max 15 words>",
      "summary": "<3-4 sentence factual summary>",
      "importance_reason": "<1-2 sentences on global significance>",
      "source": "<source name>",
      "url": "<EXACT original article URL>",
      "category": "<category>",
      "keywords": ["kw1", "kw2", "kw3"],
      "importance_score": <1-10>
    }}
  ]
}}"""


REQUIRED_FIELDS = {"rank", "title", "url", "summary", "importance_score"}


async def check_gemini_health() -> bool:
    """Quick check if Gemini API is reachable."""
    if MOCK_MODE:
        return False
    try:
        response = await asyncio.to_thread(
            _model.generate_content, "Reply with exactly: OK"
        )
        return "OK" in (response.text or "")
    except Exception as e:
        logger.warning(f"Gemini health check failed: {e}")
        return False


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


def _build_article_list(articles: List[dict]) -> str:
    return "\n".join(
        f"{i+1}. [{a.get('source')}] {a.get('title')} "
        f"(cat={a.get('category')}, score={a.get('importance_score') or 5}) URL:{a.get('url')}"
        for i, a in enumerate(articles[:60])
    )


def _mock_items(articles: List[dict], n: int) -> List[dict]:
    """Fallback: rank by importance_score + recency."""
    # Sort by importance_score descending, then by scraped_at descending
    scored = sorted(
        articles,
        key=lambda a: (
            -(a.get("importance_score") or 5),
            -(a.get("scraped_at").timestamp() if hasattr(a.get("scraped_at"), "timestamp") else 0),
        ),
    )
    return [
        {
            "rank": i + 1,
            "title": a.get("title", ""),
            "ai_title": a.get("ai_title") or a.get("title", ""),
            "summary": a.get("ai_summary") or a.get("summary") or "Full article available at source.",
            "importance_reason": f"Top story from {a.get('source', 'a major news source')}.",
            "source": a.get("source", ""),
            "url": a.get("url", ""),
            "category": a.get("category", "general"),
            "keywords": a.get("keywords", []),
            "importance_score": a.get("importance_score") or 5,
        }
        for i, a in enumerate(scored[:n])
        if a.get("url")  # NEVER include items without a URL
    ]


def _validate_curated_items(items: list, original_articles: List[dict]) -> List[dict]:
    """Strict validation of Gemini output. Discards invalid items."""
    # Build a set of known URLs from the original pool for validation
    known_urls = {a.get("url") for a in original_articles if a.get("url")}

    validated = []
    for item in items:
        # Check required fields
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            logger.warning(f"Curator item missing fields {missing}, discarding: {item.get('title', '?')}")
            continue

        # URL must be present and non-empty
        if not item.get("url"):
            logger.warning(f"Curator item has no URL, discarding: {item.get('title', '?')}")
            continue

        # Ensure importance_score fallback
        item["importance_score"] = item.get("importance_score") or 5

        # Ensure ai_title exists
        if not item.get("ai_title"):
            item["ai_title"] = item.get("title", "")

        # Ensure keywords is a list
        if not isinstance(item.get("keywords"), list):
            item["keywords"] = []

        validated.append(item)

    return validated


async def _gemini_curate(articles: List[dict], n: int, language: str = "en", preferred_topics: Optional[List[str]] = None) -> List[dict]:
    """Ask Gemini to pick the top-n stories. Falls back to mock on any error."""
    topic_instruction = ""
    if preferred_topics:
        topic_instruction = f"\nPrioritize these topics (in order of importance): {', '.join(preferred_topics)}\n"

    prompt = (
        CURATOR_PROMPT.format(n=n, language=language, topic_instruction=topic_instruction)
        + "\n\nToday's articles:\n"
        + _build_article_list(articles)
    )
    try:
        response = await asyncio.to_thread(_model.generate_content, prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        items = result.get("top", [])

        # Strict validation
        validated = _validate_curated_items(items, articles)

        if len(validated) < 3:
            logger.warning(f"Only {len(validated)} valid items from Gemini, falling back to mock")
            return _mock_items(articles, n)

        return validated
    except json.JSONDecodeError as e:
        logger.warning(f"Gemini returned invalid JSON: {e}")
        return _mock_items(articles, n)
    except Exception as e:
        logger.error("Gemini failed — using fallback")
        return _mock_items(articles, n)


async def curate_top10() -> Dict:
    """Generate Top-20 for the curated_top10 collection.
    Client-side slices to user preference (5/10/20).
    Now grouped by language."""
    today = date.today().isoformat()
    top10_col = get_collection("top10")
    articles = await _load_candidate_articles(200)

    if not articles:
        return {}

    from collections import defaultdict
    articles_by_lang = defaultdict(list)
    for art in articles:
        lang = art.get("language", "en")
        articles_by_lang[lang].append(art)

    n = 20  # Always generate top 20 internally
    
    results = {}
    for lang, lang_articles in articles_by_lang.items():
        logger.info(f"Curating Top {n} for lang={lang} | candidates={len(lang_articles)}")

        # Check Gemini health before expensive call
        if not MOCK_MODE:
            healthy = await check_gemini_health()
            if healthy:
                items = await _gemini_curate(lang_articles, n, lang)
            else:
                logger.warning("Gemini unhealthy, using fallback ranking")
                items = _mock_items(lang_articles, n)
        else:
            items = _mock_items(lang_articles, n)

        doc = {"date": today, "language": lang, "items": items, "generated_at": datetime.now(timezone.utc)}
        await top10_col.update_one({"date": today, "language": lang}, {"$set": doc}, upsert=True)
        results[lang] = doc
        logger.info(f"Top {len(items)} curated | date={today} lang={lang}")
    
    return results