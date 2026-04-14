"""
AI processing service using Google Gemini Flash.
Falls back gracefully to mock mode if no API key is configured.
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    _gemini_available = True
except ImportError:
    _gemini_available = False
    logger.warning("google-generativeai not installed. Running in mock mode.")

MOCK_MODE = not settings.gemini_api_key or not _gemini_available

if not MOCK_MODE:
    genai.configure(api_key=settings.gemini_api_key)
    _model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=400,
        ),
    )

_STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
}

SYSTEM_PROMPT = """You are a professional news editor. Process the given news article.
Return ONLY a valid JSON object with these fields:
- ai_title: Clean, engaging rewritten headline (max 15 words)
- summary: Clear 3-5 sentence summary of the article
- category: One of: general, world, politics, sports, business, technology, science, health, entertainment, india, geopolitics
- keywords: Array of 3-6 lowercase relevant keywords

Return ONLY the JSON object, no markdown fences, no extra text."""


async def _process_with_gemini(article: dict) -> Optional[dict]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Category: {article.get('category', '')}\n"
        f"Snippet: {article.get('summary', '')[:300]}"
    )
    try:
        # Run sync Gemini call in a thread to avoid blocking async loop
        response = await asyncio.to_thread(_model.generate_content, prompt)
        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
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
    """Find unprocessed articles and run Gemini AI on them."""
    collection = get_collection("news")
    stats = {"processed": 0, "errors": 0}

    cursor = collection.find({"processed": False}).sort("scraped_at", -1).limit(100)
    articles = await cursor.to_list(length=100)
    logger.info(f"AI processing {len(articles)} articles (mock={MOCK_MODE})...")

    for article in articles:
        try:
            if MOCK_MODE:
                result = _mock_process(article)
            else:
                result = await _process_with_gemini(article) or _mock_process(article)
                # Small delay to respect Gemini rate limits (15 RPM on free tier)
                await asyncio.sleep(1.5)

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
