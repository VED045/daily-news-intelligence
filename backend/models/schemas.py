"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr


class ArticleResponse(BaseModel):
    id: Optional[str] = None
    title: str
    ai_title: Optional[str] = None
    url: str
    source: str
    category: str = "general"
    published_at: Optional[str] = None
    summary: Optional[str] = None
    ai_summary: Optional[str] = None
    keywords: List[str] = []
    image_url: Optional[str] = None

    class Config:
        populate_by_name = True


class Top10Item(BaseModel):
    rank: int
    title: str
    ai_title: str
    summary: str
    importance_reason: str
    source: str
    url: str
    category: str
    keywords: List[str] = []


class Top10Response(BaseModel):
    date: str
    items: List[Top10Item]
    generated_at: Optional[str] = None


class TrendData(BaseModel):
    date: str
    category_counts: Dict[str, int] = {}
    trending_keywords: List[Dict[str, Any]] = []
    most_covered: str = "N/A"
    total_articles: int = 0


class SubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class NewsListResponse(BaseModel):
    articles: List[Dict[str, Any]]
    total: int
    page: int
    has_more: bool


# ── New schemas for personalization ──────────────────────────

class BookmarkCreate(BaseModel):
    articleId: str


class PreferencesUpdate(BaseModel):
    preferred_topics: Optional[List[str]] = None
    top_n_preference: Optional[int] = None  # 5, 10, or 20


class PreferencesResponse(BaseModel):
    preferred_topics: List[str] = []
    top_n_preference: int = 10
    is_subscribed_email: bool = True
