"""
Dainik-Vidya — FastAPI Backend Entry Point
"""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import connect_db, close_db
from routes import news, top5, trends, subscription, search
from scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Dainik-Vidya API...")
    await connect_db()
    start_scheduler()
    yield
    logger.info("Shutting down...")
    stop_scheduler()
    await close_db()


app = FastAPI(
    title="Dainik-Vidya API",
    description="Hybrid RSS + NewsAPI news aggregation with Gemini AI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://dainik-vidya.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router,         prefix="/news",       tags=["News"])
app.include_router(top5.router,         prefix="/top5",       tags=["Top 5"])
app.include_router(trends.router,       prefix="/trends",     tags=["Trends"])
app.include_router(subscription.router,                       tags=["Subscription"])
app.include_router(search.router,       prefix="/search",     tags=["Search"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "Dainik-Vidya", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/trigger-pipeline", tags=["Admin"])
async def trigger_pipeline():
    """Manually trigger the full hybrid pipeline (RSS + NewsAPI + AI)."""
    from services.pipeline import run_full_pipeline
    import asyncio
    asyncio.create_task(run_full_pipeline())
    return {
        "message": "Hybrid pipeline triggered in background",
        "steps": ["rss_scrape", "news_api", "dedup", "ai_rank", "curate", "trends", "email"],
    }


@app.get("/pipeline/status", tags=["Admin"])
async def pipeline_status():
    """Return quick stats about the current state of the DB."""
    from database import get_collection
    news_col = get_collection("news")
    total      = await news_col.count_documents({})
    processed  = await news_col.count_documents({"processed": True})
    unprocessed = await news_col.count_documents({"processed": False})
    return {
        "total_articles": total,
        "processed": processed,
        "unprocessed": unprocessed,
    }
