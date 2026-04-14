"""
Bookmarks routes — Dainik-Vidya
POST   /bookmark          — save an article
GET    /bookmarks         — list all saved + full article data
DELETE /bookmark/{id}     — remove a bookmark
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from database import get_collection

router = APIRouter()
logger = logging.getLogger(__name__)


class BookmarkCreate(BaseModel):
    articleId: str


def _ser_bm(bm: dict) -> dict:
    bm["_id"] = str(bm["_id"])
    if "savedAt" in bm and hasattr(bm["savedAt"], "isoformat"):
        bm["savedAt"] = bm["savedAt"].isoformat() + "Z"
    return bm


def _ser_article(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in ("published_at", "scraped_at", "processed_at"):
        val = doc.get(field)
        if val and hasattr(val, "isoformat"):
            doc[field] = val.isoformat() if val.tzinfo else val.isoformat() + "Z"
    doc["publishedAt"]     = doc.get("published_at")
    doc["imageUrl"]        = doc.get("image_url")
    doc["importanceScore"] = doc.get("importance_score")
    doc["sourceType"]      = "News API" if doc.get("source_type") == "newsapi" else "Scraped"
    doc["contentPreview"]  = doc.get("content_preview", "")
    return doc


@router.post("")
async def add_bookmark(body: BookmarkCreate):
    """Save an article to bookmarks."""
    if not ObjectId.is_valid(body.articleId):
        raise HTTPException(status_code=400, detail="Invalid article ID")

    bm_col   = get_collection("bookmarks")
    news_col = get_collection("news")

    # Check article exists
    article = await news_col.find_one({"_id": ObjectId(body.articleId)})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Prevent duplicate bookmarks
    existing = await bm_col.find_one({"articleId": body.articleId})
    if existing:
        return {"message": "Already bookmarked", "id": str(existing["_id"])}

    doc = {"articleId": body.articleId, "savedAt": datetime.now(timezone.utc)}
    result = await bm_col.insert_one(doc)
    return {"message": "Bookmarked", "id": str(result.inserted_id)}


@router.get("")
async def get_bookmarks():
    """Return all bookmarks with full article data."""
    bm_col   = get_collection("bookmarks")
    news_col = get_collection("news")

    bookmarks = await bm_col.find({}).sort("savedAt", -1).to_list(200)
    articles  = []
    for bm in bookmarks:
        article_id = bm.get("articleId", "")
        if not ObjectId.is_valid(article_id):
            continue
        art = await news_col.find_one({"_id": ObjectId(article_id)})
        if art:
            serialised        = _ser_article(art)
            serialised["bookmarkId"] = str(bm["_id"])
            serialised["savedAt"]    = bm["savedAt"].isoformat() + "Z" if hasattr(bm.get("savedAt"), "isoformat") else ""
            articles.append(serialised)

    return {"bookmarks": articles, "total": len(articles)}


@router.delete("/{bookmark_id}")
async def remove_bookmark(bookmark_id: str):
    """Remove a bookmark by its ID."""
    if not ObjectId.is_valid(bookmark_id):
        raise HTTPException(status_code=400, detail="Invalid bookmark ID")

    bm_col = get_collection("bookmarks")
    result = await bm_col.delete_one({"_id": ObjectId(bookmark_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed"}


@router.delete("/article/{article_id}")
async def remove_bookmark_by_article(article_id: str):
    """Remove a bookmark by the article ID (convenient for toggle)."""
    bm_col = get_collection("bookmarks")
    result = await bm_col.delete_one({"articleId": article_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed"}
