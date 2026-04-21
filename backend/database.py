"""
MongoDB async connection using Motor.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from core.logger import get_logger

logger = get_logger()
_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    """Initialize MongoDB connection."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        # Parse DB name from URI or use default
        uri_path = settings.mongodb_uri.split("/")
        db_name = uri_path[-1].split("?")[0] if len(uri_path) > 3 and uri_path[-1] else "dailynews"
        _db = _client[db_name]
        await _client.admin.command("ping")
        logger.info("✅ Connected to MongoDB")
        # Create indexes for performance
        await _db["news"].create_index("url_hash", unique=True)
        await _db["news"].create_index([("published_at", -1)])
        await _db["news"].create_index("category")
        await _db["top10"].create_index("date", unique=True)
        await _db["trends"].create_index("date", unique=True)
        await _db["users"].create_index("email", unique=True)
        await _db["bookmarks"].create_index(
            [("user_id", 1), ("articleId", 1)], unique=True
        )
        await _db["news"].create_index("scraped_at")
        await _db["news"].create_index("source")
        logger.info("✅ Indexes created")
    except Exception as e:
        logger.exception("MongoDB connection failed")
        raise


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db():
    return _db


def get_collection(name: str):
    return _db[name]
