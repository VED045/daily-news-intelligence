"""
Configuration — Dainik-Vidya Backend
Loads all settings from environment variables with safe defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Database ──────────────────────────────────────────────────
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/dailynews")

    # ── AI ────────────────────────────────────────────────────────
    gemini_api_key: str       = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str         = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    groq_api_key: str         = os.getenv("GROQ_API_KEY", "")
    openrouter_api_key: str   = os.getenv("OPENROUTER_API_KEY", "")

    # ── News API ──────────────────────────────────────────────────
    news_api_key: str    = os.getenv("NEWS_API_KEY", "")

    # ── Email ─────────────────────────────────────────────────────
    smtp_host: str  = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int  = int(os.getenv("SMTP_PORT") or 587)
    smtp_user: str  = os.getenv("SMTP_USER", "")
    smtp_pass: str  = os.getenv("SMTP_PASS", "")
    from_email: str = os.getenv("FROM_EMAIL", "Dainik-Vidya <noreply@dainik-vidya.app>")

    # ── App ───────────────────────────────────────────────────────
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # ── Scheduler (IST) ───────────────────────────────────────────
    scheduler_hour: int    = int(os.getenv("SCHEDULER_HOUR")    or 7)
    scheduler_minute: int  = int(os.getenv("SCHEDULER_MINUTE")  or 0)
    scheduler_hour_2: int  = int(os.getenv("SCHEDULER_HOUR_2")  or 14)   # 2 PM IST
    scheduler_minute_2: int = int(os.getenv("SCHEDULER_MINUTE_2") or 0)

    # ── Pipeline limits ───────────────────────────────────────────
    max_scraper_articles: int  = int(os.getenv("MAX_SCRAPER_ARTICLES")  or 100)
    max_news_api_articles: int = int(os.getenv("MAX_NEWS_API_ARTICLES") or 50)
    max_ai_articles: int       = int(os.getenv("MAX_AI_ARTICLES")       or 15)

    # ── Rate control ──────────────────────────────────────────────
    gemini_rpm: int = int(os.getenv("GEMINI_RPM") or 12)   # requests / min (free tier = 15)


settings = Settings()
