"""
APScheduler: runs the full daily pipeline at 7:00 AM IST.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler = None


async def run_daily_pipeline():
    """Full pipeline: scrape → AI process → curate Top 5 → trends → email."""
    logger.info("=" * 55)
    logger.info("🚀 Daily News Intelligence Pipeline starting...")
    logger.info("=" * 55)

    try:
        from services.scraper import scrape_all_feeds
        logger.info("📡 [1/5] Scraping RSS feeds...")
        scrape_stats = await scrape_all_feeds()
        logger.info(f"     Result: {scrape_stats}")

        from services.ai_processor import process_all_unprocessed
        logger.info("🤖 [2/5] AI processing articles...")
        ai_stats = await process_all_unprocessed()
        logger.info(f"     Result: {ai_stats}")

        from services.curator import curate_top5
        logger.info("⭐ [3/5] Curating Top 5...")
        await curate_top5()

        from services.trends_service import compute_trends
        logger.info("📊 [4/5] Computing trends...")
        await compute_trends()

        from services.email_service import send_daily_digest
        logger.info("📬 [5/5] Sending email digest...")
        email_stats = await send_daily_digest()
        logger.info(f"     Result: {email_stats}")

        logger.info("✅ Daily pipeline completed successfully!")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)


def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
            timezone="Asia/Kolkata",
        ),
        id="daily_pipeline",
        name="Daily News Intelligence Pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        f"⏰ Scheduler active — pipeline runs at "
        f"{settings.scheduler_hour:02d}:{settings.scheduler_minute:02d} IST daily"
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
