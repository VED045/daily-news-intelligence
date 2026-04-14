"""
NewsAPI integration — Dainik-Vidya
Fetches up to MAX_NEWS_API_ARTICLES structured articles per run.
Uses newsapi.org top-headlines + everything endpoints.
"""
import requests
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)
NEWSAPI_BASE = "https://newsapi.org/v2"

# Fetch config — each entry defines one API call
#   type:     "top-headlines" | "everything"
#   category: NewsAPI category (top-headlines only)
#   q:        search query (everything only)
#   our_cat:  our internal category label
#   count:    max articles to pull from this call
FETCH_PLAN: List[Dict] = [
    {"type": "top-headlines", "category": "business",    "our_cat": "business",    "count": 12},
    {"type": "top-headlines", "category": "technology",  "our_cat": "technology",  "count": 12},
    {"type": "top-headlines", "category": "health",      "our_cat": "health",      "count": 8},
    {"type": "top-headlines", "category": "science",     "our_cat": "science",     "count": 6},
    {"type": "top-headlines", "category": "general",     "our_cat": "general",     "count": 6},
    # Finance: map business category + finance query
    {"type": "everything", "q": "finance OR stock market OR economy",
     "our_cat": "finance", "count": 8},
    # Politics / geopolitics
    {"type": "everything", "q": "politics OR parliament OR government OR geopolitics",
     "our_cat": "politics", "count": 10},
]


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_dt(s: Optional[str]) -> datetime:
    """Parse NewsAPI's ISO 8601 datetime string (always UTC)."""
    if not s:
        return datetime.now(timezone.utc)
    try:
        clean = s.replace("Z", "+00:00")
        return datetime.fromisoformat(clean).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


async def fetch_news_api() -> Dict[str, int]:
    """Fetch articles from NewsAPI and insert new ones into MongoDB."""
    if not settings.news_api_key:
        logger.warning("NEWS_API_KEY not set — skipping NewsAPI fetch")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

    collection = get_collection("news")
    stats = {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}
    total_new = 0
    cap = settings.max_news_api_articles

    for cfg in FETCH_PLAN:
        if total_new >= cap:
            break

        remaining = cap - total_new
        page_size = min(cfg["count"], remaining, 100)

        try:
            if cfg["type"] == "top-headlines":
                resp = requests.get(
                    f"{NEWSAPI_BASE}/top-headlines",
                    params={
                        "apiKey": settings.news_api_key,
                        "category": cfg["category"],
                        "language": "en",
                        "pageSize": page_size,
                    },
                    timeout=15,
                )
            else:
                resp = requests.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={
                        "apiKey": settings.news_api_key,
                        "q": cfg["q"],
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": page_size,
                    },
                    timeout=15,
                )

            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                msg = data.get("message", "unknown error")
                logger.warning(f"  ⚠️ NewsAPI [{cfg['our_cat']}] error: {msg}")
                stats["errors"] += 1
                continue

            batch = []
            for art in data.get("articles", []):
                url = art.get("url", "")
                # Filter out removed articles
                if not url or url == "https://removed.com":
                    continue
                title = (art.get("title") or "").strip()
                if not title or title == "[Removed]":
                    continue

                uhash = _url_hash(url)
                if await collection.find_one({"url_hash": uhash}):
                    stats["skipped"] += 1
                    continue

                # Prefer longer of description vs content
                description = (art.get("description") or "").strip()
                content     = (art.get("content") or "").strip()
                # NewsAPI truncates content at ~200 chars with "[+N chars]" suffix — clean it up
                if " [+" in content:
                    content = content[:content.index(" [+")]
                summary = content if len(content) > len(description) else description
                summary = summary[:1000]

                batch.append({
                    "title": title,
                    "url": url,
                    "url_hash": uhash,
                    "source": (art.get("source") or {}).get("name") or cfg["our_cat"].title(),
                    "category": cfg["our_cat"],
                    "published_at": _parse_dt(art.get("publishedAt")),
                    "summary": summary,
                    "ai_title": None,
                    "ai_summary": None,
                    "keywords": [],
                    "image_url": art.get("urlToImage"),
                    "importance_score": None,
                    "is_sports": cfg["our_cat"] == "sports",
                    "source_type": "newsapi",
                    "processed": False,
                    "scraped_at": datetime.now(timezone.utc),
                })
                stats["fetched"] += 1

            if batch:
                result = await collection.insert_many(batch)
                inserted = len(result.inserted_ids)
                stats["new"] += inserted
                total_new += inserted
                logger.info(f"  ✅ NewsAPI [{cfg['our_cat']}]: +{inserted} articles")

        except requests.RequestException as e:
            logger.warning(f"  ⚠️ NewsAPI [{cfg.get('category', cfg.get('q', '?'))}]: {e}")
            stats["errors"] += 1
        except Exception as e:
            logger.error(f"  ❌ NewsAPI unexpected error: {e}")
            stats["errors"] += 1

    return stats
