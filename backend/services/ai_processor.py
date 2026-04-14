"""
AI processing service using Google Gemini 3 Flash.
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

# Attempt to load Gemini
try:
    import google.generativeai as genai
    _gemini_available = True
except ImportError:
    _gemini_available = False
    logger.warning("google-generativeai not installed. Running in mock mode.")

# Determine if we should run in MOCK mode
MOCK_MODE = not settings.gemini_api_key or not _gemini_available

if not MOCK_MODE:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            model_name="gemini-3-flash",  # Using the latest Gemini 3 Flash model
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
                # Forces the model to output a valid JSON string
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")
        MOCK_MODE = True

_STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "with", "has", "have", "been", "were", "was", "will",
}

SYSTEM_PROMPT = """You are a professional news editor. 
Process the given news article and return a JSON object with these exact keys:
- ai_title: Clean, engaging rewritten headline (max 15 words)
- summary: Clear 3-5 sentence summary of the article
- category: One of: general, world, politics, sports, business, technology, science, health, entertainment, india, geopolitics
- keywords: Array of 3-6 lowercase relevant keywords"""


async def _process_with_gemini(article: dict) -> Optional[dict]:
    """Helper to call Gemini API and handle JSON response."""
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Category: {article.get('category', '')}\n"
        f"Snippet: {article.get('summary', '')[:500]}"
    )
    
    try:
        # response_mime_type="application/json" ensures we get back valid JSON
        response = await asyncio.to_thread(_model.generate_content, prompt)
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API error for article {article.get('_id')}: {e}")
        return None


def _mock_process(article: dict) -> dict:
    """Fallback logic if AI fails or is disabled."""
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
    if collection is None:
        logger.error("Database collection 'news' not available.")
        return {"processed": 0, "errors": 0}

    stats = {"processed": 0, "errors": 0}

    # Grab the most recent 100 unprocessed articles
    cursor = collection.find({"processed": False}).sort("scraped_at", -1).limit(100)
    articles = await cursor.to_list(length=100)
    
    if not articles:
        logger.info("No new articles to process.")
        return stats

    logger.info(f"AI processing {len(articles)} articles (MOCK_MODE={MOCK_MODE})...")

    for article in articles:
        try:
            if MOCK_MODE:
                result = _mock_process(article)
            else:
                # Try Gemini, fallback to Mock if it fails
                result = await _process_with_gemini(article) or _mock_process(article)
                
                # Free tier limit is usually 15 RPM; adjust sleep if on Paid tier
                await asyncio.sleep(1.2)

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
            logger.error(f"Error updating article {article.get('_id')}: {e}")
            stats["errors"] += 1

    logger.info(f"AI processing complete: {stats}")
    return stats