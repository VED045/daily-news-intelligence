"""
Personalization routes — Dainik-Vidya
All endpoints require authentication.

GET  /me/preferences   — get user preferences
PUT  /me/preferences   — update preferred_topics + top_n_preference
POST /me/subscribe     — set is_subscribed_email = True (idempotent)
POST /me/unsubscribe   — set is_subscribed_email = False (idempotent)
GET  /me/feed          — personalized news feed
""""""
Personalization routes — Dainik-Vidya
All endpoints require authentication.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_collection
from models.schemas import PreferencesUpdate
from routes.deps import get_current_user
from core.logger import get_logger

router = APIRouter()
logger = get_logger()

VALID_TOPICS = [
    "politics", "geopolitics", "business", "finance", "technology",
    "health", "science", "world", "india", "general",
    "entertainment", "sports",
]

CATEGORY_PRIORITY = {
    "politics": 1, "geopolitics": 2, "business": 3, "finance": 4,
    "technology": 5, "health": 6, "science": 7, "world": 8,
    "india": 9, "general": 10, "entertainment": 11, "sports": 12,
}

SPORTS_CATEGORIES = {"sports"}
MAX_SPORTS_IN_FEED = 1


# ✅ FIXED SERIALIZER
def _serialize(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict."""
    doc["_id"] = str(doc["_id"])

    for field in ("published_at", "scraped_at", "processed_at"):
        val = doc.get(field)
        if val and hasattr(val, "isoformat"):
            doc[field] = val.isoformat() if val.tzinfo else val.isoformat() + "Z"

    # Map frontend fields
    doc["publishedAt"] = doc.get("published_at")
    doc["imageUrl"] = doc.get("image_url")
    doc["importanceScore"] = doc.get("importance_score")
    doc["contentPreview"] = doc.get("content_preview", "")
    doc["language"] = doc.get("language", "en")

    # ✅ FIX: define source_type safely
    raw_st = doc.get("source_type", "rss")
    doc["sourceType"] = "News API" if raw_st == "newsapi" else "Scraped"

    return doc


# ── Preferences ──────────────────────────────────────────────

@router.get("/preferences")
async def get_preferences(user: dict = Depends(get_current_user)):
    users_col = get_collection("users")
    doc = await users_col.find_one({"email": user["email"]})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "preferred_topics": doc.get("preferred_topics", []),
        "top_n_preference": doc.get("top_n_preference", 10),
        "is_subscribed_email": doc.get("is_subscribed_email", True),
        "preferred_language": doc.get("preferred_language", "en"),
    }


@router.put("/preferences")
async def update_preferences(
    body: PreferencesUpdate,
    user: dict = Depends(get_current_user),
):
    users_col = get_collection("users")
    updates: dict = {"updated_at": datetime.now(timezone.utc)}

    if body.preferred_topics is not None:
        cleaned = [t.lower() for t in body.preferred_topics if t.lower() in VALID_TOPICS]
        updates["preferred_topics"] = cleaned

    if body.top_n_preference is not None:
        if body.top_n_preference not in (5, 10, 20):
            raise HTTPException(status_code=400, detail="top_n_preference must be 5, 10, or 20")
        updates["top_n_preference"] = body.top_n_preference

    if body.preferred_language is not None:
        if body.preferred_language not in ("en", "hi", "mr", "te"):
            raise HTTPException(status_code=400, detail="Invalid language")
        updates["preferred_language"] = body.preferred_language

    result = await users_col.update_one({"email": user["email"]}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message": "Preferences updated",
        "updates": {k: v for k, v in updates.items() if k != "updated_at"},
    }


# ── Subscription ─────────────────────────────────────────────

@router.post("/subscribe")
async def subscribe_email(user: dict = Depends(get_current_user)):
    users_col = get_collection("users")
    await users_col.update_one(
        {"email": user["email"]},
        {"$set": {"is_subscribed_email": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Subscribed", "is_subscribed_email": True}


@router.post("/unsubscribe")
async def unsubscribe_email(user: dict = Depends(get_current_user)):
    users_col = get_collection("users")
    await users_col.update_one(
        {"email": user["email"]},
        {"$set": {"is_subscribed_email": False, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Unsubscribed", "is_subscribed_email": False}


# ── Personalized Feed ────────────────────────────────────────

@router.get("/feed")
async def get_personalized_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    users_col = get_collection("users")
    news_col = get_collection("news")

    user_doc = await users_col.find_one({"email": user["email"]})
    preferred = user_doc.get("preferred_topics", []) if user_doc else []
    preferred_lang = user_doc.get("preferred_language", "en") if user_doc else "en"

    query: dict = {}

    if preferred:
        query["$or"] = [
            {"language": preferred_lang},
            {"language": {"$exists": False}}
        ]

    # Date filter
    if date_from:
        start = datetime.fromisoformat(date_from)
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if date_to:
        end = datetime.fromisoformat(date_to)
    else:
        end = start + timedelta(days=1)

    query["scraped_at"] = {"$gte": start, "$lt": end}

    if source:
        query["source"] = {"$regex": source, "$options": "i"}

    if category and category.lower() not in ("all", ""):
        query["category"] = {"$regex": category, "$options": "i"}
    elif preferred:
        query["category"] = {"$in": preferred}

    pool_size = max(limit * 10, 100)
    cursor = news_col.find(query).sort("scraped_at", -1).limit(pool_size)

    pool = [_serialize(doc) async for doc in cursor]

    # Sorting
    if preferred:
        priority_map = {topic: i for i, topic in enumerate(preferred)}

        def sort_key(a):
            p = priority_map.get(a.get("category", "general"), 999)
            score = -(a.get("importanceScore") or 5)
            return (p, score)

        pool.sort(key=sort_key)
    else:
        pool.sort(key=lambda a: -(a.get("importanceScore") or 5))

    # Sports cap
    result, sports_seen = [], 0
    for a in pool:
        if a.get("category") in SPORTS_CATEGORIES:
            if sports_seen < MAX_SPORTS_IN_FEED:
                result.append(a)
                sports_seen += 1
        else:
            result.append(a)

    skip = (page - 1) * limit
    page_items = result[skip: skip + limit]

    return {
        "articles": page_items,
        "total": len(result),
        "page": page,
        "has_more": (skip + limit) < len(result),
        "personalized": bool(preferred),
    }