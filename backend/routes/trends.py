"""
Analytics and trend data routes.
"""
from fastapi import APIRouter, HTTPException
from datetime import date
import logging
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_trends():
    """Get today's trend analysis data."""
    try:
        collection = get_collection("trends")
        today = date.today().isoformat()

        doc = await collection.find_one({"date": today})
        if not doc:
            doc = await collection.find_one({}, sort=[("date", -1)])

        if not doc:
            return {
                "date": today,
                "category_counts": {},
                "trending_keywords": [],
                "most_covered": "N/A",
                "total_articles": 0,
                "message": "Trend data not yet generated.",
            }

        doc["_id"] = str(doc["_id"])
        if "computed_at" in doc and doc["computed_at"]:
            doc["computed_at"] = doc["computed_at"].isoformat()
        return doc
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_trend_history(days: int = 7):
    """Get trend history for the past N days."""
    try:
        collection = get_collection("trends")
        cursor = collection.find({}).sort("date", -1).limit(days)
        history = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "computed_at" in doc and doc["computed_at"]:
                doc["computed_at"] = doc["computed_at"].isoformat()
            history.append(doc)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
