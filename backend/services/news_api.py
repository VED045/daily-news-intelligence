"""
NewsAPI integration — Dainik-Vidya
Fetches up to MAX_NEWS_API_ARTICLES structured articles per run.
Uses newsapi.org top-headlines endpoint (async httpx + tenacity retry).

Fixes applied:
  • Switched from requests (sync) to httpx (async)
  • Full error logging: status code, URL, response body
  • Tenacity retry: max 3 attempts with exponential backoff
  • Falls back gracefully (empty list) — never crashes pipeline
  • source_type="newsapi" on every article
  • language field always present
"""
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from database import get_collection
from config import settings
from core.logger import get_logger

logger = get_logger()

NEWSAPI_BASE = "https://newsapi.org/v2"

# Fetch config — each entry defines one API call
#   type:     "top-headlines" | "everything"
#   category: NewsAPI category (top-headlines only)
#   q:        search query (everything only)
#   our_cat:  our internal category label
#   count:    max articles to pull from this call
FETCH_PLAN: List[Dict] = [
    {"type": "top-headlines", "category": "business",   "our_cat": "business",   "count": 12},
    {"type": "top-headlines", "category": "technology", "our_cat": "technology", "count": 12},
    {"type": "top-headlines", "category": "health",     "our_cat": "health",     "count": 8},
    {"type": "top-headlines", "category": "science",    "our_cat": "science",    "count": 6},
    {"type": "top-headlines", "category": "general",    "our_cat": "general",    "count": 6},
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


# ── Retry decorator ──────────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _fetch_with_retry(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    """GET a NewsAPI URL with up to 3 retries on network/HTTP errors."""
    logger.debug(f"NewsAPI request → {url} params={params}")
    resp = await client.get(url, params=params, timeout=15)
    # Log full error details before raising
    if resp.status_code != 200:
        logger.error(
            f"NewsAPI HTTP error | status={resp.status_code} "
            f"url={resp.url} body={resp.text[:300]}"
        )
        resp.raise_for_status()
    return resp


async def fetch_news_api() -> Dict[str, int]:
    """Fetch articles from NewsAPI and insert new ones into MongoDB."""
    if not settings.news_api_key:
        logger.warning("⚠️ NewsAPI skipped (no key configured)")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 0,
                "news_api_used": False, "news_api_count": 0}

    logger.info("🌐 [2/6] NewsAPI fetch started")
    collection = get_collection("news")
    stats = {"fetched": 0, "new": 0, "skipped": 0, "errors": 0,
             "news_api_used": True, "news_api_count": 0}
    total_new = 0
    cap = settings.max_news_api_articles

    async with httpx.AsyncClient() as client:
        for cfg in FETCH_PLAN:
            if total_new >= cap:
                break

            remaining = cap - total_new
            page_size = min(cfg["count"], remaining, 100)

            if cfg["type"] == "top-headlines":
                endpoint = f"{NEWSAPI_BASE}/top-headlines"
                params = {
                    "apiKey": settings.news_api_key,
                    "category": cfg["category"],
                    "language": "en",
                    "pageSize": page_size,
                }
            else:
                endpoint = f"{NEWSAPI_BASE}/everything"
                params = {
                    "apiKey": settings.news_api_key,
                    "q": cfg["q"],
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": page_size,
                }

            try:
                resp = await _fetch_with_retry(client, endpoint, params)
                data = resp.json()

                if data.get("status") != "ok":
                    msg = data.get("message", "unknown error")
                    logger.error(
                        f"NewsAPI responded not-ok | cat={cfg['our_cat']} "
                        f"msg={msg} url={endpoint}"
                    )
                    stats["errors"] += 1
                    continue

                batch = []
                for art in data.get("articles", []):
                    url = art.get("url", "")
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
                    content = (art.get("content") or "").strip()
                    # NewsAPI truncates content with "[+N chars]" — clean up
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
                        "content_preview": summary[:300] if summary else "",
                        "ai_title": None,
                        "ai_summary": None,
                        "keywords": [],
                        "ai_used": False,
                        "language": "en",          # NewsAPI always returns English
                        "image_url": art.get("urlToImage"),
                        "importance_score": 5,
                        "is_sports": cfg["our_cat"] == "sports",
                        "source_type": "newsapi",  # always tag source
                        "processed": False,
                        "scraped_at": datetime.now(timezone.utc),
                    })
                    stats["fetched"] += 1

                if batch:
                    result = await collection.insert_many(batch)
                    inserted = len(result.inserted_ids)
                    stats["new"] += inserted
                    total_new += inserted
                    logger.info(
                        f"✅ NewsAPI success | cat={cfg['our_cat']} inserted={inserted}"
                    )

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.error(
                    f"NewsAPI FAILED → using RSS fallback | cat={cfg['our_cat']} "
                    f"error={type(e).__name__}: {e}"
                )
                stats["errors"] += 1
            except Exception as e:
                logger.error(
                    f"NewsAPI unexpected error | cat={cfg['our_cat']} "
                    f"error={type(e).__name__}: {e}"
                )
                stats["errors"] += 1

    stats["news_api_count"] = total_new
    logger.info(f"📊 NewsAPI success count: {total_new}")
    if stats["errors"]:
        logger.warning(f"NewsAPI FAILED → using RSS fallback | failed_calls={stats['errors']}")
    return stats
