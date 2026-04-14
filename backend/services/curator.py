"""
Curator service: selects Top 5 most important stories using AI.
"""
import json
import logging
from datetime import datetime, date
from typing import Dict, List
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    _openai_available = True
except ImportError:
    _openai_available = False

MOCK_MODE = not settings.openai_api_key or not _openai_available

if not MOCK_MODE:
    _client = AsyncOpenAI(api_key=settings.openai_api_key)

CURATOR_PROMPT = """You are a senior international news editor.
Given today's news headlines, select the 5 most globally important stories.
Prioritize: geopolitics, major world events, economic impact, policy changes.
De-prioritize: celebrity news, minor local stories.

Return ONLY a JSON object:
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

    # Fallback to latest articles if today's batch is small
    if len(articles) < 5:
        cursor = news_col.find({"processed": True}).sort("scraped_at", -1).limit(50)
        articles = await cursor.to_list(length=50)

    if not articles:
        logger.warning("No articles available for Top 5 curation")
        return {}

    if MOCK_MODE:
        return await _mock_curate(articles, today, top5_col)

    article_lines = [
        f"{i+1}. [{a.get('source')}] {a.get('ai_title') or a.get('title')} "
        f"(Category: {a.get('category')}) URL: {a.get('url')}"
        for i, a in enumerate(articles[:40])
    ]

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CURATOR_PROMPT},
                {"role": "user", "content": "Today's articles:\n" + "\n".join(article_lines)},
            ],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
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
