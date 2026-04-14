"""
AI processing service using OpenAI GPT-4o-mini.
Falls back gracefully to mock mode if no API key is set.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    _openai_available = True
except ImportError:
    _openai_available = False
    logger.warning("openai package not installed. Running in mock mode.")

MOCK_MODE = not settings.openai_api_key or not _openai_available

if not MOCK_MODE:
    _client = AsyncOpenAI(api_key=settings.openai_api_key)

_STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
}

SYSTEM_PROMPT = """You are a professional news editor. Process the given news article and return ONLY a JSON object with these fields:
- ai_title: Clean, engaging rewritten headline (max 15 words)
- summary: Clear 3-5 sentence summary
- category: One of: general, world, politics, sports, business, technology, science, health, entertainment, india, geopolitics
- keywords: Array of 3-6 lowercase relevant keywords
Return ONLY the JSON object."""


async def _process_with_ai(article: dict) -> Optional[dict]:
    user_content = (
        f"Title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Category: {article.get('category', '')}\n"
        f"Snippet: {article.get('summary', '')[:300]}"
    )
    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return None


def _mock_process(article: dict) -> dict:
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
    }


async def process_all_unprocessed() -> Dict[str, int]:
    """Find unprocessed articles and run AI on them."""
    collection = get_collection("news")
    stats = {"processed": 0, "errors": 0}

    cursor = collection.find({"processed": False}).sort("scraped_at", -1).limit(100)
    articles = await cursor.to_list(length=100)
    logger.info(f"AI processing {len(articles)} articles (mock={MOCK_MODE})...")

    for article in articles:
        try:
            result = (
                _mock_process(article)
                if MOCK_MODE
                else (await _process_with_ai(article) or _mock_process(article))
            )
            await collection.update_one(
                {"_id": article["_id"]},
                {
                    "$set": {
                        "ai_title": result.get("ai_title", article.get("title")),
                        "ai_summary": result.get("summary", ""),
                        "category": result.get("category", article.get("category")),
                        "keywords": result.get("keywords", []),
                        "processed": True,
                        "processed_at": datetime.utcnow(),
                    }
                },
            )
            stats["processed"] += 1
        except Exception as e:
            logger.error(f"Error processing {article.get('_id')}: {e}")
            stats["errors"] += 1

    logger.info(f"AI processing done: {stats}")
    return stats
