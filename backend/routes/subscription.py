"""
Email subscription management routes.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import logging
from database import get_collection
from models.schemas import SubscribeRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    """Subscribe an email to the daily digest."""
    try:
        collection = get_collection("users")
        existing = await collection.find_one({"email": request.email})

        if existing:
            if existing.get("active", True):
                return {"message": "Already subscribed!", "email": request.email}
            # Re-activate
            await collection.update_one(
                {"email": request.email},
                {"$set": {"active": True, "subscribed_at": datetime.utcnow()}},
            )
            return {"message": "Welcome back! Subscription reactivated.", "email": request.email}

        await collection.insert_one(
            {
                "email": request.email,
                "name": request.name or "",
                "active": True,
                "subscribed_at": datetime.utcnow(),
            }
        )
        return {"message": "Successfully subscribed to Daily News Intelligence!", "email": request.email}
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unsubscribe")
async def unsubscribe(email: str = Query(..., description="Email to unsubscribe")):
    """Unsubscribe from the daily digest."""
    try:
        collection = get_collection("users")
        result = await collection.update_one({"email": email}, {"$set": {"active": False}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Email not found")
        return {"message": "Successfully unsubscribed.", "email": email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
