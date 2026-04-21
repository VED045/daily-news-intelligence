"""
Full-text search routes.
"""
from fastapi import APIRouter, Query, HTTPException
from database import get_collection
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.get("")
async def search_news(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Search articles by keyword in title, summary, or tags."""
    try:
        collection = get_collection("news")
        skip = (page - 1) * limit

        query = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"ai_title": {"$regex": q, "$options": "i"}},
                {"ai_summary": {"$regex": q, "$options": "i"}},
                {"keywords": {"$elemMatch": {"$regex": q, "$options": "i"}}},
                {"source": {"$regex": q, "$options": "i"}},
            ]
        }

        cursor = collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "published_at" in doc and doc["published_at"]:
                doc["published_at"] = doc["published_at"].isoformat()
            articles.append(doc)

        total = await collection.count_documents(query)

        return {
            "query": q,
            "articles": articles,
            "total": total,
            "page": page,
            "has_more": (skip + limit) < total,
        }
    except Exception as e:
        logger.exception(f"Search error | q={q}")
        raise HTTPException(status_code=500, detail=str(e))
