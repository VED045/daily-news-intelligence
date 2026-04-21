"""
Top 10 AI-curated articles route.
"""
from fastapi import APIRouter, HTTPException
from datetime import date
from database import get_collection
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.get("")
async def get_top10(language: str = "en"):
    """Get today's top 10 AI-curated news stories for a specific language."""
    try:
        collection = get_collection("top10")
        today = date.today().isoformat()

        doc = await collection.find_one({"date": today, "language": language})
        if not doc:
            doc = await collection.find_one({"language": language}, sort=[("date", -1)])

        if not doc:
            return {
                "date": today,
                "language": language,
                "items": [],
                "message": "Top 10 not yet generated for this language. Trigger the pipeline or wait for the scheduler.",
            }

        doc["_id"] = str(doc["_id"])
        if "generated_at" in doc and doc["generated_at"]:
            doc["generated_at"] = doc["generated_at"].isoformat()
        return doc
    except Exception as e:
        logger.exception("Error fetching top10")
        raise HTTPException(status_code=500, detail=str(e))

