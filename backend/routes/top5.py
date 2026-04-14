"""
Top 5 AI-curated articles route.
"""
from fastapi import APIRouter, HTTPException
from datetime import date
import logging
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_top5():
    """Get today's top 5 AI-curated news stories."""
    try:
        collection = get_collection("top5")
        today = date.today().isoformat()

        doc = await collection.find_one({"date": today})
        if not doc:
            doc = await collection.find_one({}, sort=[("date", -1)])

        if not doc:
            return {
                "date": today,
                "items": [],
                "message": "Top 5 not yet generated. Trigger the pipeline or wait for the scheduler.",
            }

        doc["_id"] = str(doc["_id"])
        if "generated_at" in doc and doc["generated_at"]:
            doc["generated_at"] = doc["generated_at"].isoformat()
        return doc
    except Exception as e:
        logger.error(f"Error fetching top5: {e}")
        raise HTTPException(status_code=500, detail=str(e))
