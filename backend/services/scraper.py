"""
News scraper — Dainik-Vidya
Sources: BBC, Reuters, The Hindu, ESPN (capped), TOI, Moneycontrol,
         Yahoo Finance, CNBC, MarketWatch, NYT Business
Rules:
 - Total scraped per run: max 100 new articles
 - Sports (ESPN / BBC Sport / TOI Sports): max 2 articles per feed, capped at 10% of total
 - Finance: dedicated category from financial RSS feeds
 - Content: extract up to 1000 chars per article for quality summaries
 - content_preview: 5-6 sentences extracted from <p> tags (BeautifulSoup)
 - source_type: "rss" for all scraped articles
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

# Max articles to add per pipeline run (keeps us well under any API/server limits)
MAX_TOTAL_NEW = 100

# How many entries to pull per feed (non-sports)
DEFAULT_FEED_LIMIT = 8

# Sports feeds get a hard cap per feed
SPORTS_FEED_LIMIT = 2

# RSS Feed configuration  — is_sports=True → hard-capped
RSS_FEEDS = [
    # ── BBC ──────────────────────────────────────────────────────────────────
    {"url": "http://feeds.bbci.co.uk/news/rss.xml",         "source": "BBC News",        "category": "general",  "is_sports": False},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml",   "source": "BBC World",        "category": "world",    "is_sports": False},
    {"url": "http://feeds.bbci.co.uk/news/politics/rss.xml","source": "BBC Politics",     "category": "politics", "is_sports": False},
    {"url": "http://feeds.bbci.co.uk/sport/rss.xml",        "source": "BBC Sport",        "category": "sports",   "is_sports": True},
    # ── Reuters ──────────────────────────────────────────────────────────────
    {"url": "https://feeds.reuters.com/reuters/topNews",     "source": "Reuters",          "category": "general",  "is_sports": False},
    {"url": "https://feeds.reuters.com/reuters/worldNews",   "source": "Reuters World",    "category": "world",    "is_sports": False},
    {"url": "https://feeds.reuters.com/reuters/businessNews","source": "Reuters Business", "category": "business", "is_sports": False},
    # ── The Hindu ────────────────────────────────────────────────────────────
    {"url": "https://www.thehindu.com/feeder/default.rss",                          "source": "The Hindu",           "category": "india",    "is_sports": False},
    {"url": "https://www.thehindu.com/news/international/feeder/default.rss",       "source": "The Hindu World",     "category": "world",    "is_sports": False},
    {"url": "https://www.thehindu.com/business/feeder/default.rss",                 "source": "The Hindu Business",  "category": "business", "is_sports": False},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss",            "source": "The Hindu National",  "category": "politics", "is_sports": False},
    # ── Times of India ───────────────────────────────────────────────────────
    {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",  "source": "Times of India",  "category": "india",    "is_sports": False},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",  "source": "TOI Business",    "category": "business", "is_sports": False},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",    "source": "TOI Sports",      "category": "sports",   "is_sports": True},
    # ── ESPN ─────────────────────────────────────────────────────────────────
    {"url": "https://www.espn.com/espn/rss/news",           "source": "ESPN",             "category": "sports",   "is_sports": True},
    # ── Moneycontrol ─────────────────────────────────────────────────────────
    {"url": "https://www.moneycontrol.com/rss/latestnews.xml",    "source": "Moneycontrol",         "category": "finance",  "is_sports": False},
    {"url": "https://www.moneycontrol.com/rss/marketreports.xml", "source": "Moneycontrol Markets", "category": "finance",  "is_sports": False},
    # ── FINANCE sources ──────────────────────────────────────────────────────
    {"url": "https://finance.yahoo.com/news/rssindex",             "source": "Yahoo Finance",  "category": "finance",  "is_sports": False},
    {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html","source": "CNBC",          "category": "finance",  "is_sports": False},
    {"url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "source": "CNBC Markets", "category": "finance",  "is_sports": False},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "source": "NYT Business","category": "finance", "is_sports": False},
]

CATEGORY_MAP = {
    "general": "general",   "world": "world",           "sports": "sports",
    "india": "india",       "business": "business",     "markets": "finance",
    "technology": "technology", "science": "science",   "health": "health",
    "entertainment": "entertainment", "politics": "politics",
    "geopolitics": "geopolitics",    "finance": "finance",
}


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_date(entry) -> datetime:
    """Parse UTC publish time from feed entry."""
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            t = entry.published_parsed
            return datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=timezone.utc)
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            t = entry.updated_parsed
            return datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)


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


def _extract_rich_content(entry) -> str:
    """
    Extract the richest available text: prefer full content > summary > title.
    Returns up to 1000 chars of plain text. Used as the article 'summary'.
    """
    text = ""

    # 1. Try content:encoded / atom:content (full article body in some feeds)
    if hasattr(entry, "content") and entry.content:
        for c in entry.content:
            v = c.get("value", "")
            if v:
                text = v
                break

    # 2. Fall back to summary
    if not text and hasattr(entry, "summary"):
        text = entry.summary or ""

    # 3. Strip HTML and normalise whitespace
    if text:
        soup = BeautifulSoup(text, "html.parser")
        text = " ".join(soup.get_text(separator=" ").split())

    return text[:1000]


def _extract_content_preview(entry) -> str:
    """
    Extract 5-6 lines of actual article content from <p> tags.
    This is separate from summary — used for the content_preview field.
    Falls back to summary text if no <p> tags found.
    Returns plain text, HTML-cleaned.
    """
    raw_html = ""

    # Try full content (HTML body)
    if hasattr(entry, "content") and entry.content:
        for c in entry.content:
            v = c.get("value", "")
            if v:
                raw_html = v
                break

    # Fall back to summary HTML
    if not raw_html and hasattr(entry, "summary"):
        raw_html = entry.summary or ""

    if not raw_html:
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        paragraphs = soup.find_all("p")

        if paragraphs:
            # Extract text from first 6 <p> tags, skip empty ones
            sentences = []
            for p in paragraphs:
                text = p.get_text(separator=" ").strip()
                # Skip very short or navigation-like snippets
                if text and len(text) > 30:
                    sentences.append(text)
                if len(sentences) >= 6:
                    break
            if sentences:
                preview = " ".join(sentences)
                return preview[:1500]

        # No <p> tags found — fall back to plain text from entire content
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:800]

    except Exception:
        return ""


async def scrape_all_feeds() -> Dict[str, int]:
    """Scrape all RSS feeds. Caps: 100 new total, ≤2 per sports feed."""
    collection = get_collection("news")
    stats = {"total_fetched": 0, "new_articles": 0, "duplicates": 0, "errors": 0}
    global_new = 0  # running count of newly inserted articles

    for feed_cfg in RSS_FEEDS:
        if global_new >= MAX_TOTAL_NEW:
            logger.info("Reached 100-article cap — stopping scrape.")
            break

        url = feed_cfg["url"]
        source = feed_cfg["source"]
        default_category = feed_cfg["category"]
        is_sports = feed_cfg.get("is_sports", False)
        per_feed_limit = SPORTS_FEED_LIMIT if is_sports else DEFAULT_FEED_LIMIT

        try:
            logger.info(f"Scraping {source} (cap={per_feed_limit})...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            batch = []
            for entry in feed.entries[:per_feed_limit]:
                if global_new + len(batch) >= MAX_TOTAL_NEW:
                    break

                article_url = entry.get("link", "")
                if not article_url:
                    continue

                uhash = _url_hash(article_url)
                existing = await collection.find_one({"url_hash": uhash})
                if existing:
                    stats["duplicates"] += 1
                    continue

                title = entry.get("title", "Untitled").strip()
                summary = _extract_rich_content(entry)
                content_preview = _extract_content_preview(entry)

                # Category detection: tag → default
                category = default_category
                if hasattr(entry, "tags") and entry.tags:
                    tag = entry.tags[0].get("term", "").lower()
                    if tag in CATEGORY_MAP:
                        category = CATEGORY_MAP[tag]

                published = _parse_date(entry)

                batch.append({
                    "title": title,
                    "url": article_url,
                    "url_hash": uhash,
                    "source": source,
                    "category": _normalize_category(category),
                    "published_at": published,           # UTC datetime with tz
                    "summary": summary,
                    "content_preview": content_preview,  # 5-6 lines from <p> tags
                    "source_type": "rss",                # "rss" for all scraped articles
                    "ai_title": None,
                    "ai_summary": None,
                    "keywords": [],
                    "image_url": _extract_image(entry),
                    "is_sports": is_sports,
                    "processed": False,
                    "scraped_at": datetime.now(timezone.utc),
                })
                stats["total_fetched"] += 1

            if batch:
                result = await collection.insert_many(batch)
                inserted = len(result.inserted_ids)
                stats["new_articles"] += inserted
                global_new += inserted
                logger.info(f"  ✅ {source}: +{inserted} articles (running total: {global_new})")

        except requests.RequestException as e:
            logger.warning(f"  ⚠️ {source} fetch failed: {e}")
            stats["errors"] += 1
        except Exception as e:
            logger.error(f"  ❌ {source} error: {e}")
            stats["errors"] += 1

    logger.info(f"Scraping complete: {stats}")
    return stats
