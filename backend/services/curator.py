"""
Curator service: selects Top 5 most important stories using Gemini Flash.
"""
import json
import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    _gemini_available = True
except ImportError:
    _gemini_available = False

MOCK_MODE = not settings.gemini_api_key or not _gemini_available

if not MOCK_MODE:
    genai.configure(api_key=settings.gemini_api_key)
    _model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2000,
        ),
    )

CURATOR_PROMPT = """You are a senior international news editor.
Given today's news headlines, select the 5 most globally important stories.
Prioritize: geopolitics, major world events, economic impact, policy changes.
De-prioritize: celebrity news, minor local stories.

Return ONLY a valid JSON object (no markdown fences):
{
  "top5": [
    {
      "rank": 1,
      "title": "original title",
      "ai_title": "compelling rewritten headline",
      "summary": "3-4 sentence factual summary",
      "importance_reason": "1-2 sentence explanation of global significance",
      "source": "source name",
      "url": "article url",
      "category": "category",
      "keywords": ["kw1", "kw2", "kw3"]
    }
  ]
}"""


async def curate_top5() -> Dict:
    """Select and rank the top 5 stories. Store in DB."""
    news_col = get_collection("news")
    top5_col = get_collection("top5")
    today = date.today().isoformat()

    from_date = datetime.combine(date.today(), datetime.min.time())
    cursor = news_col.find({"scraped_at": {"$gte": from_date}, "processed": True}).limit(50)
    articles = await cursor.to_list(length=50)

    if len(articles) < 5:
        cursor = news_col.find({"processed": True}).sort("scraped_at", -1).limit(50)
        articles = await cursor.to_list(length=50)

    if not articles:
        logger.warning("No articles available for Top 5 curation")
        return {}

    if MOCK_MODE:
        return await _mock_curate(articles, today, top5_col)

    article_lines = "\n".join(
        f"{i+1}. [{a.get('source')}] {a.get('ai_title') or a.get('title')} "
        f"(Category: {a.get('category')}) URL: {a.get('url')}"
        for i, a in enumerate(articles[:40])
    )
    prompt = f"{CURATOR_PROMPT}\n\nToday's articles:\n{article_lines}"

    try:
        response = await asyncio.to_thread(_model.generate_content, prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        items = result.get("top5", [])
    except Exception as e:
        logger.error(f"Curation error: {e}")
        return await _mock_curate(articles, today, top5_col)

    doc = {"date": today, "items": items, "generated_at": datetime.utcnow()}
    await top5_col.update_one({"date": today}, {"$set": doc}, upsert=True)
    logger.info(f"✅ Top 5 curated for {today}")
    return doc


async def _mock_curate(articles: List[Dict], today: str, col) -> Dict:
    items = [
        {
            "rank": i + 1,
            "title": a.get("title", ""),
            "ai_title": a.get("ai_title") or a.get("title", ""),
            "summary": a.get("ai_summary") or a.get("summary") or "Full article available at source.",
            "importance_reason": f"Selected as a top story from {a.get('source', 'a major news source')}.",
            "source": a.get("source", ""),
            "url": a.get("url", ""),
            "category": a.get("category", "general"),
            "keywords": a.get("keywords", []),
        }
        for i, a in enumerate(articles[:5])
    ]
    doc = {"date": today, "items": items, "generated_at": datetime.utcnow()}
    await col.update_one({"date": today}, {"$set": doc}, upsert=True)
    return doc
