"""
Curator service: selects Top 10 most important stories using Gemini 3 Flash.
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
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            model_name="gemini-3-flash",
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=3000,
                response_mime_type="application/json", # Native JSON mode
            ),
        )
    except Exception as e:
        logger.error(f"Failed to configure Curator Gemini: {e}")
        MOCK_MODE = True

CURATOR_PROMPT = """You are a senior international news editor.
Given today's news headlines, select the 10 most globally important stories.
Prioritize: geopolitics, major world events, economic impact, and breakthrough policy changes.
De-prioritize: celebrity gossip, local sports, or minor regional news.

Return a JSON object with this exact structure:
{
  "top10": [
    {
      "rank": 1,
      "title": "original headline",
      "ai_title": "engaging and professional rewritten headline",
      "summary": "3-4 sentence factual summary of the core event",
      "importance_reason": "Clear explanation of why this story has global significance",
      "source": "source name",
      "url": "article url",
      "category": "category",
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }
  ]
}"""


async def curate_top10() -> Dict:
    """Select and rank the top 10 stories. Store in DB."""
    news_col = get_collection("news")
    top10_col = get_collection("top10")  # Updated collection name
    today = date.today().isoformat()

    # Try to get articles from the last 24 hours first
    from_date = datetime.combine(date.today(), datetime.min.time())
    cursor = news_col.find({"scraped_at": {"$gte": from_date}, "processed": True}).limit(60)
    articles = await cursor.to_list(length=60)

    # Fallback if today's scraping is low
    if len(articles) < 10:
        cursor = news_col.find({"processed": True}).sort("scraped_at", -1).limit(60)
        articles = await cursor.to_list(length=60)

    if not articles:
        logger.warning("No articles available for Top 10 curation")
        return {}

    if MOCK_MODE:
        return await _mock_curate(articles, today, top10_col)

    # Prepare article list for the prompt
    article_lines = "\n".join(
        f"{i+1}. [{a.get('source')}] {a.get('ai_title') or a.get('title')} "
        f"(Category: {a.get('category')}) URL: {a.get('url')}"
        for i, a in enumerate(articles[:50])
    )
    prompt = f"{CURATOR_PROMPT}\n\nToday's processed articles:\n{article_lines}"

    try:
        # Gemini 3 Flash in JSON mode
        response = await asyncio.to_thread(_model.generate_content, prompt)
        result = json.loads(response.text)
        items = result.get("top10", [])
        
        # Validate we actually got 10 (or as many as possible)
        if not items:
            raise ValueError("Empty items list from AI")
            
    except Exception as e:
        logger.error(f"Curation error: {e}. Falling back to mock.")
        return await _mock_curate(articles, today, top10_col)

    doc = {
        "date": today, 
        "items": items, 
        "generated_at": datetime.utcnow(),
        "count": len(items)
    }
    
    # Use 'date' as unique index to avoid duplicates
    await top10_col.update_one({"date": today}, {"$set": doc}, upsert=True)
    logger.info(f"✅ Top 10 curated for {today}")
    return doc


async def _mock_curate(articles: List[Dict], today: str, col) -> Dict:
    """Fallback ranking logic if AI fails."""
    items = [
        {
            "rank": i + 1,
            "title": a.get("title", ""),
            "ai_title": a.get("ai_title") or a.get("title", ""),
            "summary": a.get("ai_summary") or a.get("summary") or "Full article available at source.",
            "importance_reason": f"System selected story from {a.get('source', 'reliable source')}.",
            "source": a.get("source", ""),
            "url": a.get("url", ""),
            "category": a.get("category", "general"),
            "keywords": a.get("keywords", []),
        }
        for i, a in enumerate(articles[:10])
    ]
    doc = {"date": today, "items": items, "generated_at": datetime.utcnow(), "count": len(items)}
    await col.update_one({"date": today}, {"$set": doc}, upsert=True)
    return doc