"""
Curator — Dainik-Vidya
Generates:
  • Top 10  highlights  (premium dashboard section)
  • Top 10 main feed   (curated_top10 collection)
Uses Gemini Flash for intelligent selection when available.
"""
import json
import asyncio
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List

from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

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
        generation_config=genai.types.GenerationConfig(temperature=0.2, max_output_tokens=3000),
    )

CURATOR_PROMPT = """\
You are a senior international news editor curating today's most important stories.
Given today's headlines, select the {n} most globally significant stories.
Prioritise: geopolitics, elections, economic crises, major world events.
De-prioritise: celebrity, minor local sports.

Return ONLY valid JSON (no markdown fences):
{{
  "top": [
    {{
      "rank": 1,
      "title": "<original title>",
      "ai_title": "<compelling rewrite, max 15 words>",
      "summary": "<3-4 sentence factual summary>",
      "importance_reason": "<1-2 sentences on global significance>",
      "source": "<source name>",
      "url": "<article url>",
      "category": "<category>",
      "keywords": ["kw1", "kw2", "kw3"],
      "importance_score": <1-10>
    }}
  ]
}}"""


async def _load_candidate_articles(limit: int = 60) -> List[dict]:
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
        f"{i+1}. [{a.get('source')}] {a.get('ai_title') or a.get('title')} "
        f"(cat={a.get('category')}, score={a.get('importance_score', '?')}) URL:{a.get('url')}"
        for i, a in enumerate(articles[:50])
    )


def _mock_items(articles: List[dict], n: int) -> List[dict]:
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
        for i, a in enumerate(articles[:n])
    ]


async def _gemini_curate(articles: List[dict], n: int) -> List[dict]:
    """Ask Gemini to pick the top-n stories. Falls back to mock on any error."""
    prompt = (
        CURATOR_PROMPT.format(n=n)
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
        return result.get("top", [])
    except Exception as e:
        logger.debug(f"Gemini curation error: {e}")
        return _mock_items(articles, n)



async def curate_top10() -> Dict:
    """Generate Top-10 main feed for the curated_top10 collection."""
    today = date.today().isoformat()
    top10_col = get_collection("top10")
    articles = await _load_candidate_articles(80)

    if not articles:
        return {}

    logger.info(f"Curating Top 10 from {len(articles)} candidates...")
    items = await _gemini_curate(articles, 10) if not MOCK_MODE else _mock_items(articles, 10)

    doc = {"date": today, "items": items, "generated_at": datetime.now(timezone.utc)}
    await top10_col.update_one({"date": today}, {"$set": doc}, upsert=True)
    logger.info(f"  ✅ Top 10 curated for {today}")
    return doc