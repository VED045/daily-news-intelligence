"""
Bookmarks routes — Dainik-Vidya
All endpoints require authentication (user-specific bookmarks).

POST   /bookmark              — save an article (user-scoped)
GET    /bookmark               — list current user's bookmarks + full article data
DELETE /bookmark/{id}          — remove a bookmark (ownership verified)
DELETE /bookmark/article/{id}  — remove by article ID (user-scoped)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from database import get_collection
from models.schemas import BookmarkCreate
from routes.deps import get_current_user
from core.logger import get_logger

router = APIRouter()
logger = get_logger()


def _ser_article(doc: dict) -> dict:
    """Convert MongoDB article doc to JSON-safe dict."""
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
async def add_bookmark(body: BookmarkCreate, user: dict = Depends(get_current_user)):
    """Save an article to bookmarks (user-specific)."""
    if not ObjectId.is_valid(body.articleId):
        raise HTTPException(status_code=400, detail="Invalid article ID")

    bm_col   = get_collection("bookmarks")
    news_col = get_collection("news")
    user_id  = user["email"]

    # Check article exists
    article = await news_col.find_one({"_id": ObjectId(body.articleId)})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Prevent duplicate bookmarks for this user (unique index also enforces)
    existing = await bm_col.find_one({"user_id": user_id, "articleId": body.articleId})
    if existing:
        return {"message": "Already bookmarked", "id": str(existing["_id"])}

    doc = {
        "user_id": user_id,
        "articleId": body.articleId,
        "savedAt": datetime.now(timezone.utc),
    }
    result = await bm_col.insert_one(doc)
    return {"message": "Bookmarked", "id": str(result.inserted_id)}


@router.get("")
async def get_bookmarks(user: dict = Depends(get_current_user)):
    """Return only this user's bookmarks with full article data."""
    bm_col   = get_collection("bookmarks")
    news_col = get_collection("news")
    user_id  = user["email"]

    bookmarks = await bm_col.find({"user_id": user_id}).sort("savedAt", -1).to_list(200)
    articles  = []
    for bm in bookmarks:
        article_id = bm.get("articleId", "")
        if not ObjectId.is_valid(article_id):
            continue
        art = await news_col.find_one({"_id": ObjectId(article_id)})
        if art:
            serialised = _ser_article(art)
            serialised["bookmarkId"] = str(bm["_id"])
            serialised["savedAt"] = (
                bm["savedAt"].isoformat() + "Z"
                if hasattr(bm.get("savedAt"), "isoformat") else ""
            )
            articles.append(serialised)

    return {"bookmarks": articles, "total": len(articles)}


@router.delete("/{bookmark_id}")
async def remove_bookmark(bookmark_id: str, user: dict = Depends(get_current_user)):
    """Remove a bookmark by its ID (ownership verified)."""
    if not ObjectId.is_valid(bookmark_id):
        raise HTTPException(status_code=400, detail="Invalid bookmark ID")

    bm_col  = get_collection("bookmarks")
    user_id = user["email"]

    bm = await bm_col.find_one({"_id": ObjectId(bookmark_id)})
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    if bm.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your bookmark")

    await bm_col.delete_one({"_id": ObjectId(bookmark_id)})
    return {"message": "Bookmark removed"}


@router.delete("/article/{article_id}")
async def remove_bookmark_by_article(article_id: str, user: dict = Depends(get_current_user)):
    """Remove a bookmark by the article ID (user-scoped)."""
    bm_col  = get_collection("bookmarks")
    user_id = user["email"]

    result = await bm_col.delete_one({"user_id": user_id, "articleId": article_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed"}
