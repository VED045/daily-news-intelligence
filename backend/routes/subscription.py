"""
Email subscription management routes (Legacy / Unauthenticated).
Auth-protected subscriptions should use the /me/subscribe routes in personalization.py.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from database import get_collection
from models.schemas import SubscribeRequest
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    """Subscribe an email to the daily digest (Legacy)."""
    try:
        collection = get_collection("users")
        existing = await collection.find_one({"email": request.email})

        now = datetime.now(timezone.utc)

        if existing:
            if existing.get("is_subscribed_email", existing.get("active", True)):
                return {"message": "Already subscribed!", "email": request.email}
            # Re-activate
            await collection.update_one(
                {"email": request.email},
                {"$set": {"is_subscribed_email": True, "active": True, "updated_at": now}},
            )
            return {"message": "Welcome back! Subscription reactivated.", "email": request.email}

        await collection.insert_one(
            {
                "email": request.email,
                "name": request.name or "",
                "is_subscribed_email": True,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        return {"message": "Successfully subscribed to Daily News Intelligence!", "email": request.email}
    except Exception as e:
        logger.exception("Subscribe error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unsubscribe")
async def unsubscribe(email: str = Query(..., description="Email to unsubscribe")):
    """Unsubscribe from the daily digest (Legacy)."""
    try:
        collection = get_collection("users")
        result = await collection.update_one(
            {"email": email},
            {"$set": {"is_subscribed_email": False, "active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Email not found")
        return {"message": "Successfully unsubscribed.", "email": email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
