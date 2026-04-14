"""
Configuration settings loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/dailynews")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    from_email: str = os.getenv("FROM_EMAIL", "Daily News Intelligence <noreply@dailynews.app>")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    # Scheduler: run at 7:00 AM IST every day
    scheduler_hour: int = int(os.getenv("SCHEDULER_HOUR", "7"))
    scheduler_minute: int = int(os.getenv("SCHEDULER_MINUTE", "0"))


settings = Settings()
