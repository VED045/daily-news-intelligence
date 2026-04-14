"""
News scraper service using RSS feeds.
Sources: BBC, Reuters, The Hindu, ESPN, Times of India, Moneycontrol
"""
import feedparser
import requests
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from database import get_collection

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# All RSS feed sources
RSS_FEEDS = [
    # BBC
    {"url": "http://feeds.bbci.co.uk/news/rss.xml", "source": "BBC News", "category": "general"},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World", "category": "world"},
    {"url": "http://feeds.bbci.co.uk/sport/rss.xml", "source": "BBC Sport", "category": "sports"},
    # Reuters
    {"url": "https://feeds.reuters.com/reuters/topNews", "source": "Reuters", "category": "general"},
    {"url": "https://feeds.reuters.com/reuters/worldNews", "source": "Reuters World", "category": "world"},
    {"url": "https://feeds.reuters.com/reuters/businessNews", "source": "Reuters Business", "category": "business"},
    # The Hindu
    {"url": "https://www.thehindu.com/feeder/default.rss", "source": "The Hindu", "category": "india"},
    {"url": "https://www.thehindu.com/news/international/feeder/default.rss", "source": "The Hindu World", "category": "world"},
    {"url": "https://www.thehindu.com/business/feeder/default.rss", "source": "The Hindu Business", "category": "business"},
    # ESPN
    {"url": "https://www.espn.com/espn/rss/news", "source": "ESPN", "category": "sports"},
    # Times of India
    {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "source": "Times of India", "category": "india"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "source": "TOI Business", "category": "business"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms", "source": "TOI Sports", "category": "sports"},
    # Moneycontrol
    {"url": "https://www.moneycontrol.com/rss/latestnews.xml", "source": "Moneycontrol", "category": "business"},
    {"url": "https://www.moneycontrol.com/rss/marketreports.xml", "source": "Moneycontrol Markets", "category": "markets"},
]

CATEGORY_MAP = {
    "general": "general", "world": "world", "sports": "sports",
    "india": "india", "business": "business", "markets": "business",
    "technology": "technology", "science": "science", "health": "health",
    "entertainment": "entertainment", "politics": "politics", "geopolitics": "geopolitics",
}


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_date(entry) -> datetime:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.utcnow()


def _extract_image(entry) -> Optional[str]:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "media_content") and entry.media_content:
        for mc in entry.media_content:
            if mc.get("type", "").startswith("image"):
                return mc.get("url")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("url")
    return None


def _normalize_category(cat: str) -> str:
    return CATEGORY_MAP.get(cat.lower(), "general")


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ").strip()[:500]


async def scrape_all_feeds() -> Dict[str, int]:
    """Scrape all RSS feeds, deduplicate, and store in MongoDB."""
    collection = get_collection("news")
    stats = {"total_fetched": 0, "new_articles": 0, "duplicates": 0, "errors": 0}

    for feed_cfg in RSS_FEEDS:
        url = feed_cfg["url"]
        source = feed_cfg["source"]
        default_category = feed_cfg["category"]

        try:
            logger.info(f"Scraping {source}...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            batch = []
            for entry in feed.entries[:20]:
                article_url = entry.get("link", "")
                if not article_url:
                    continue

                uhash = _url_hash(article_url)
                existing = await collection.find_one({"url_hash": uhash})
                if existing:
                    stats["duplicates"] += 1
                    continue

                title = entry.get("title", "Untitled").strip()
                summary = _clean_html(entry.get("summary", ""))

                # Try to detect category from tags
                category = default_category
                if hasattr(entry, "tags") and entry.tags:
                    tag = entry.tags[0].get("term", "").lower()
                    if tag in CATEGORY_MAP:
                        category = tag

                batch.append({
                    "title": title,
                    "url": article_url,
                    "url_hash": uhash,
                    "source": source,
                    "category": _normalize_category(category),
                    "published_at": _parse_date(entry),
                    "summary": summary,
                    "ai_title": None,
                    "ai_summary": None,
                    "keywords": [],
                    "image_url": _extract_image(entry),
                    "processed": False,
                    "scraped_at": datetime.utcnow(),
                })
                stats["total_fetched"] += 1

            if batch:
                result = await collection.insert_many(batch)
                stats["new_articles"] += len(result.inserted_ids)
                logger.info(f"  ✅ {source}: +{len(result.inserted_ids)} articles")

        except requests.RequestException as e:
            logger.warning(f"  ⚠️ {source} fetch failed: {e}")
            stats["errors"] += 1
        except Exception as e:
            logger.error(f"  ❌ {source} error: {e}")
            stats["errors"] += 1

    logger.info(f"Scraping complete: {stats}")
    return stats
