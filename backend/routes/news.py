"""
News articles API — Dainik-Vidya
GET /news                    → Priority-sorted articles with date/source/topic filters
GET /news/{id}               → Single article
GET /news/sources            → Distinct source names
GET /news/categories/counts  → Category counts (only where count > 0)
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from database import get_collection
from core.logger import get_logger

router = APIRouter()
logger = get_logger()

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
    doc["publishedAt"]     = doc.get("published_at")
    doc["imageUrl"]        = doc.get("image_url")
    doc["importanceScore"] = doc.get("importance_score") or 5

    raw_st = doc.get("source_type", "rss")
    doc["sourceType"] = "News API" if raw_st == "newsapi" else "Scraped"

    # Content preview (5-6 lines of article body)
    doc["contentPreview"] = doc.get("content_preview", "")
    doc["language"] = doc.get("language", "en")

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


def _parse_date_range(date_from: Optional[str], date_to: Optional[str]):
    """Parse date range strings into datetime objects. Returns (start, end) or (None, None)."""
    if not date_from:
        return None, None
    try:
        start = datetime.fromisoformat(date_from)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except ValueError:
        return None, None
    if date_to:
        try:
            end = datetime.fromisoformat(date_to)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
        except ValueError:
            end = start + timedelta(days=1)
    else:
        end = start + timedelta(days=1)
    return start, end


@router.get("/sources")
async def get_sources():
    """Return distinct source names in the database."""
    try:
        collection = get_collection("news")
        sources = await collection.distinct("source")
        # Filter out empty strings
        sources = [s for s in sources if s]
        sources.sort()
        return {"sources": sources}
    except Exception as e:
        logger.exception("get_sources error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/counts")
async def get_category_counts(
    date_from: Optional[str] = Query(None, description="ISO date e.g. 2026-04-21"),
    date_to: Optional[str] = Query(None),
):
    """Return {category: count} only for categories with count > 0."""
    try:
        collection = get_collection("news")
        query: dict = {}

        start, end = _parse_date_range(date_from, date_to)
        if start and end:
            query["scraped_at"] = {"$gte": start, "$lt": end}

        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 0}}},
        ]
        results = {}
        async for doc in collection.aggregate(pipeline):
            cat = doc["_id"]
            if cat:
                results[cat] = doc["count"]
        return {"category_counts": results}
    except Exception as e:
        logger.exception("get_category_counts error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_news(
    category: Optional[str] = Query(None),
    page:     int           = Query(1, ge=1),
    limit:    int           = Query(DEFAULT_LIMIT, ge=1, le=50),
    topic:    Optional[str] = Query(None, description="Filter by keyword/topic"),
    date_from: Optional[str] = Query(None, description="ISO date e.g. 2026-04-21"),
    date_to:  Optional[str] = Query(None),
    source:   Optional[str] = Query(None, description="Filter by source name"),
    language: str           = Query("en", description="Filter by language (en, hi, mr, te)"),
):
    """
    Return priority-sorted news articles.
    Supports date range, source, category, language, and topic filters.
    """
    try:
        collection = get_collection("news")
        query: dict = {"language": language}

        # Date range filter
        start, end = _parse_date_range(date_from, date_to)
        if start and end:
            query["scraped_at"] = {"$gte": start, "$lt": end}

        # Source filter
        if source:
            query["source"] = {"$regex": source, "$options": "i"}

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
        logger.exception("get_news error")
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
