"""
Analytics and trend data routes.
"""
from fastapi import APIRouter, HTTPException
from datetime import date
from database import get_collection
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.get("")
async def get_trends(language: str = "en"):
    """Get today's trend analysis data for a specific language."""
    try:
        collection = get_collection("trends")
        today = date.today().isoformat()

        doc = await collection.find_one({"date": today, "language": language})
        if not doc:
            doc = await collection.find_one({"language": language}, sort=[("date", -1)])

        if not doc:
            return {
                "date": today,
                "language": language,
                "category_counts": {},
                "trending_keywords": [],
                "top_themes": [],
                "overview": "Trend data not yet generated for this language.",
                "category_insights": {},
                "most_covered": "N/A",
                "total_articles": 0,
                "message": "Trend data not yet generated.",
            }

        doc["_id"] = str(doc["_id"])
        if "computed_at" in doc and doc["computed_at"]:
            doc["computed_at"] = doc["computed_at"].isoformat()
        return doc
    except Exception as e:
        logger.exception("Error fetching trends")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_trend_history(days: int = 7, language: str = "en"):
    """Get trend history for the past N days."""
    try:
        collection = get_collection("trends")
        cursor = collection.find({"language": language}).sort("date", -1).limit(days)
        history = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "computed_at" in doc and doc["computed_at"]:
                doc["computed_at"] = doc["computed_at"].isoformat()
            history.append(doc)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
