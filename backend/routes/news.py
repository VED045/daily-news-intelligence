"""
News articles API — Dainik-Vidya
GET /news          → Top 10 priority-sorted articles (default)
GET /news/{id}     → Single article
Response includes importanceScore for frontend sorting.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging
from bson import ObjectId
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Priority lookup (matches pipeline.py) ──────────────────
CATEGORY_PRIORITY = {
    "politics":      1, "geopolitics":   2,
    "business":      3, "finance":       4,
    "technology":    5, "health":        6,
    "science":       7, "world":         8,
    "india":         9, "general":       10,
    "entertainment": 11, "sports":       12,
}
SPORTS_CATEGORIES = {"sports"}
MAX_SPORTS_IN_FEED = 1
DEFAULT_LIMIT = 10


def _serialize(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict with proper field names."""
    doc["_id"] = str(doc["_id"])

    # Ensure all datetime fields carry UTC timezone suffix for frontend
    for field in ("published_at", "scraped_at", "processed_at"):
        val = doc.get(field)
        if val and hasattr(val, "isoformat"):
            doc[field] = val.isoformat() if val.tzinfo else val.isoformat() + "Z"

    # Alias publishedAt for frontend compatibility
    doc["publishedAt"] = doc.get("published_at")
    doc["imageUrl"]    = doc.get("image_url")
    doc["importanceScore"] = doc.get("importance_score")

    return doc


def _priority_sort(articles: List[dict]) -> List[dict]:
    def key(a):
        p = CATEGORY_PRIORITY.get(a.get("category", "general"), 10)
        # Secondary: importance score (higher = better, so negate)
        score = -(a.get("importance_score") or 5)
        # Tertiary: recency
        pub = a.get("published_at")
        ts = -(pub.timestamp() if hasattr(pub, "timestamp") else 0)
        return (p, score, ts)
    return sorted(articles, key=key)


def _apply_sports_cap(articles: List[dict], cap: int = MAX_SPORTS_IN_FEED) -> List[dict]:
    result, sports_seen = [], 0
    for a in articles:
        if a.get("category") in SPORTS_CATEGORIES:
            if sports_seen < cap:
                result.append(a)
                sports_seen += 1
        else:
            result.append(a)
    return result


@router.get("")
async def get_news(
    category: Optional[str] = Query(None),
    page:     int           = Query(1, ge=1),
    limit:    int           = Query(DEFAULT_LIMIT, ge=1, le=50),
    topic:    Optional[str] = Query(None, description="Filter by keyword/topic"),
):
    """
    Return priority-sorted news articles.
    Default: top 10, sports capped at 1.
    """
    try:
        collection = get_collection("news")
        query: dict = {}

        if category and category.lower() not in ("all", ""):
            query["category"] = {"$regex": category, "$options": "i"}

        if topic:
            query["$or"] = [
                {"keywords": {"$elemMatch": {"$regex": topic, "$options": "i"}}},
                {"ai_title": {"$regex": topic, "$options": "i"}},
                {"title":    {"$regex": topic, "$options": "i"}},
            ]

        cat_filter_active = bool(category and category.lower() not in ("all", ""))

        if cat_filter_active:
            skip = (page - 1) * limit
            cursor = (
                collection.find(query)
                .sort([("importance_score", -1), ("published_at", -1)])
                .skip(skip).limit(limit)
            )
            articles = [_serialize(doc) async for doc in cursor]
            total = await collection.count_documents(query)
            return {"articles": articles, "total": total, "page": page,
                    "has_more": (skip + limit) < total}

        # Default: pull a large pool, priority-sort, sports-cap, paginate
        pool_size = max(limit * 8, 80)
        cursor = (
            collection.find(query)
            .sort([("published_at", -1)])
            .limit(pool_size)
        )
        pool = [_serialize(doc) async for doc in cursor]
        sorted_pool  = _priority_sort(pool)
        capped       = _apply_sports_cap(sorted_pool, MAX_SPORTS_IN_FEED)
        skip         = (page - 1) * limit
        page_items   = capped[skip: skip + limit]

        return {
            "articles": page_items,
            "total":    len(capped),
            "page":     page,
            "has_more": (skip + limit) < len(capped),
        }

    except Exception as e:
        logger.error(f"get_news error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{article_id}")
async def get_article(article_id: str):
    """Fetch a single article by MongoDB ObjectId."""
    try:
        if not ObjectId.is_valid(article_id):
            raise HTTPException(status_code=400, detail="Invalid article ID")
        collection = get_collection("news")
        doc = await collection.find_one({"_id": ObjectId(article_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Article not found")
        return _serialize(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
