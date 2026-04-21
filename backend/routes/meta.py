"""
Metadata route — Dainik-Vidya
GET /meta — returns last pipeline run time + total article count
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from database import get_collection
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


async def update_last_fetched(news_api_count: int = 0, rss_count: int = 0):
    """Called by pipeline after each successful run."""
    meta_col  = get_collection("metadata")
    news_col  = get_collection("news")
    total     = await news_col.count_documents({})
    processed = await news_col.count_documents({"processed": True})

    await meta_col.update_one(
        {"key": "pipeline_last_run"},
        {"$set": {
            "key":          "pipeline_last_run",
            "lastFetchedAt": datetime.now(timezone.utc),
            "totalArticles": total,
            "processedArticles": processed,
            "news_api_count": news_api_count,
            "rss_count": rss_count,
        }},
        upsert=True,
    )


@router.get("")
async def get_meta():
    """Return last fetch time and article counts."""
    meta_col  = get_collection("metadata")
    news_col  = get_collection("news")

    doc   = await meta_col.find_one({"key": "pipeline_last_run"})
    total = await news_col.count_documents({})

    last_fetched = None
    if doc and doc.get("lastFetchedAt"):
        dt = doc["lastFetchedAt"]
        last_fetched = dt.isoformat() + "Z" if not dt.tzinfo else dt.isoformat()

    return {
        "lastFetchedAt":     last_fetched,
        "totalArticles":     total,
        "processedArticles": doc.get("processedArticles", 0) if doc else 0,
        "news_api_count":    doc.get("news_api_count", 0) if doc else 0,
        "rss_count":         doc.get("rss_count", 0) if doc else 0,
    }
