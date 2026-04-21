"""
APScheduler — Dainik-Vidya
Runs the full hybrid pipeline at:
  • 07:00 AM IST (morning edition)
  • 02:00 PM IST (afternoon edition)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
from core.logger import get_logger

logger = get_logger()
_scheduler: AsyncIOScheduler = None


async def run_daily_pipeline():
    """Entry point called by both scheduler jobs and /trigger-pipeline."""
    from services.pipeline import run_full_pipeline
    await run_full_pipeline()


def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # ── Job 1: Morning — 7:00 AM IST ──────────────────────────────
    _scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
            timezone="Asia/Kolkata",
        ),
        id="morning_pipeline",
        name="Morning Pipeline (7 AM IST)",
        replace_existing=True,
    )

    # ── Job 2: Afternoon — 2:00 PM IST ────────────────────────────
    _scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(
            hour=settings.scheduler_hour_2,
            minute=settings.scheduler_minute_2,
            timezone="Asia/Kolkata",
        ),
        id="afternoon_pipeline",
        name="Afternoon Pipeline (2 PM IST)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"⏰ Scheduler active — pipeline runs at "
        f"{settings.scheduler_hour:02d}:{settings.scheduler_minute:02d} IST "
        f"and {settings.scheduler_hour_2:02d}:{settings.scheduler_minute_2:02d} IST"
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
