"""
Daily News Intelligence — FastAPI Backend Entry Point
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
    logger.info("🚀 Starting Daily News Intelligence API...")
    await connect_db()
    start_scheduler()
    yield
    logger.info("Shutting down...")
    stop_scheduler()
    await close_db()


app = FastAPI(
    title="Daily News Intelligence API",
    description="AI-powered news aggregation and analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://dainik-vidya.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router, prefix="/news", tags=["News"])
app.include_router(top5.router, prefix="/top5", tags=["Top 5"])
app.include_router(trends.router, prefix="/trends", tags=["Trends"])
app.include_router(subscription.router, tags=["Subscription"])
app.include_router(search.router, prefix="/search", tags=["Search"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Daily News Intelligence API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/trigger-pipeline", tags=["Admin"])
async def trigger_pipeline():
    """Manually trigger the full data pipeline (for testing)."""
    from scheduler.jobs import run_daily_pipeline
    import asyncio
    asyncio.create_task(run_daily_pipeline())
    return {"message": "Pipeline triggered in background"}
