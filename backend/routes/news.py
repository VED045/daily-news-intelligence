"""
News articles API routes.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging
from bson import ObjectId
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if "published_at" in doc and doc["published_at"]:
        doc["published_at"] = doc["published_at"].isoformat()
    if "scraped_at" in doc and doc["scraped_at"]:
        doc["scraped_at"] = doc["scraped_at"].isoformat()
    if "processed_at" in doc and doc["processed_at"]:
        doc["processed_at"] = doc["processed_at"].isoformat()
    return doc


@router.get("")
async def get_news(
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated news articles with optional category filter."""
    try:
        collection = get_collection("news")
        skip = (page - 1) * limit

        query = {}
        if category and category.lower() != "all":
            query["category"] = {"$regex": category, "$options": "i"}

        cursor = collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
        articles = [_serialize(doc) async for doc in cursor]
        total = await collection.count_documents(query)

        return {
            "articles": articles,
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
