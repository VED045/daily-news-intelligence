"""
News articles API routes — Dainik-Vidya.
Default feed: top 10, priority-sorted, sports capped at 1.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging
from bson import ObjectId
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)

# Lower number = higher priority in the feed
CATEGORY_PRIORITY = {
    "politics":      1,
    "geopolitics":   2,
    "business":      3,
    "finance":       4,
    "technology":    5,
    "health":        6,
    "science":       7,
    "world":         8,
    "india":         9,
    "general":       10,
    "entertainment": 11,
    "sports":        12,
}

SPORTS_CATEGORIES = {"sports"}
MAX_SPORTS_IN_FEED = 1      # max sports articles in the default top-10 feed
DEFAULT_FEED_SIZE = 10


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    # Ensure published_at carries timezone info so frontend can convert correctly
    for field in ("published_at", "scraped_at", "processed_at"):
        if field in doc and doc[field]:
            dt = doc[field]
            # If it's already a string, leave it; otherwise isoformat with Z suffix
            if hasattr(dt, "isoformat"):
                doc[field] = dt.isoformat() if dt.tzinfo else dt.isoformat() + "Z"
    return doc


def _priority_sort(articles: List[dict]) -> List[dict]:
    """Sort articles by category priority, then by publish time (newer first)."""
    from datetime import datetime

    def sort_key(a):
        priority = CATEGORY_PRIORITY.get(a.get("category", "general"), 10)
        pub = a.get("published_at") or ""
        # Reverse-chronological within each priority group
        return (priority, pub)

    return sorted(articles, key=sort_key)


def _apply_sports_cap(articles: List[dict], max_sports: int = MAX_SPORTS_IN_FEED) -> List[dict]:
    """Keep at most `max_sports` sports articles in the list."""
    result = []
    sports_count = 0
    for a in articles:
        if a.get("category") in SPORTS_CATEGORIES:
            if sports_count < max_sports:
                result.append(a)
                sports_count += 1
        else:
            result.append(a)
    return result


@router.get("")
async def get_news(
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_FEED_SIZE, ge=1, le=50),
    topic: Optional[str] = Query(None, description="Filter by trending topic keyword"),
):
    """
    Get top-priority news articles.
    - Default limit = 10
    - Priority order: politics → geopolitics → business → finance → tech → health → sports
    - Sports capped at 1 when no category filter is applied
    """
    try:
        collection = get_collection("news")

        query = {}
        if category and category.lower() not in ("all", ""):
            query["category"] = {"$regex": category, "$options": "i"}
        if topic:
            query["$or"] = [
                {"keywords": {"$elemMatch": {"$regex": topic, "$options": "i"}}},
                {"ai_title": {"$regex": topic, "$options": "i"}},
                {"title": {"$regex": topic, "$options": "i"}},
            ]

        category_filter_active = bool(category and category.lower() not in ("all", ""))

        if category_filter_active:
            # Simple paginated response for a specific category
            skip = (page - 1) * limit
            cursor = collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
            articles = [_serialize(doc) async for doc in cursor]
            total = await collection.count_documents(query)
            return {
                "articles": articles,
                "total": total,
                "page": page,
                "has_more": (skip + limit) < total,
            }
        else:
            # Priority-sorted, sports-capped feed
            # Pull a larger pool to sort, then trim to limit
            pool_size = max(limit * 8, 80)
            cursor = collection.find(query).sort("published_at", -1).limit(pool_size)
            pool = [_serialize(doc) async for doc in cursor]

            sorted_pool = _priority_sort(pool)
            capped = _apply_sports_cap(sorted_pool, MAX_SPORTS_IN_FEED)

            skip = (page - 1) * limit
            page_articles = capped[skip: skip + limit]
            total = len(capped)

            return {
                "articles": page_articles,
                "total": total,
                "page": page,
                "has_more": (skip + limit) < total,
            }

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{article_id}")
async def get_article(article_id: str):
    """Get a single article by ID."""
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
