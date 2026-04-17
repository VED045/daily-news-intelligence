"""
Email digest service: sends daily newsletter to all active subscribers via SMTP.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date
from typing import Dict, List
from database import get_collection
from config import settings

logger = logging.getLogger(__name__)


def _build_html(top10: List[Dict], headlines: List[Dict], trends: Dict, date_str: str, email: str) -> str:
    unsub_url = f"{settings.frontend_url}/subscribe?unsubscribe={email}"

    top10_html = "".join(
        f"""<div style="background:#1e293b;border-left:4px solid #6366f1;padding:16px;margin-bottom:12px;border-radius:6px;">
        <span style="color:#818cf8;font-size:11px;font-weight:700;">#{item.get('rank')} — {item.get('category','').upper()}</span>
        <h3 style="color:#f1f5f9;margin:8px 0 6px;font-size:16px;">{item.get('ai_title') or item.get('title','')}</h3>
        <p style="color:#94a3b8;font-size:13px;line-height:1.7;margin:0 0 8px;">{item.get('summary','')}</p>
        <p style="color:#64748b;font-size:12px;font-style:italic;margin:0 0 8px;">💡 {item.get('importance_reason','')}</p>
        <a href="{item.get('url','#')}" style="color:#818cf8;font-size:13px;text-decoration:none;">Read full story →</a></div>"""
        for item in top10[:10]
    )

    headlines_html = "".join(
        f"""<div style="border-bottom:1px solid #1e293b;padding:10px 0;">
        <a href="{a.get('url','#')}" style="color:#cbd5e1;text-decoration:none;font-size:14px;">{a.get('ai_title') or a.get('title','')}</a>
        <span style="color:#475569;font-size:12px;margin-left:8px;">— {a.get('source','')}</span></div>"""
        for a in headlines[:10]
    )

    kws = trends.get("trending_keywords", [])[:10]
    tags_html = " ".join(
        f'<span style="background:#1e3a5f;color:#60a5fa;padding:4px 12px;border-radius:20px;font-size:12px;display:inline-block;margin:3px;">{k["word"]}</span>'
        for k in kws
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily News Intelligence</title></head>
<body style="background:#0f172a;color:#e2e8f0;font-family:'Helvetica Neue',Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px;">
  <div style="text-align:center;padding:28px 0 20px;">
    <div style="font-size:32px;margin-bottom:8px;">📰</div>
    <h1 style="color:#818cf8;font-size:26px;margin:0 0 4px;">Daily News Intelligence</h1>
    <p style="color:#475569;font-size:14px;margin:0;">{date_str}</p>
  </div>
  <div style="background:#1a2540;border-radius:12px;padding:24px;margin-bottom:20px;">
    <h2 style="color:#f1f5f9;font-size:18px;border-bottom:1px solid #334155;padding-bottom:12px;margin-top:0;">🔥 Top 10 Today</h2>
    {top10_html if top10_html else '<p style="color:#64748b;">Top 10 not yet generated today.</p>'}
  </div>
  <div style="background:#1a2540;border-radius:12px;padding:24px;margin-bottom:20px;">
    <h2 style="color:#f1f5f9;font-size:18px;border-bottom:1px solid #334155;padding-bottom:12px;margin-top:0;">📋 More Headlines</h2>
    {headlines_html}
  </div>
  <div style="background:#1a2540;border-radius:12px;padding:24px;margin-bottom:20px;">
    <h2 style="color:#f1f5f9;font-size:18px;border-bottom:1px solid #334155;padding-bottom:12px;margin-top:0;">📊 Trending Today</h2>
    <div style="line-height:2;">{tags_html or '<p style="color:#64748b;">No trending data yet.</p>'}</div>
  </div>
  <div style="text-align:center;padding:16px;color:#334155;font-size:12px;">
    <p>You subscribed to Daily News Intelligence daily digest.</p>
    <a href="{unsub_url}" style="color:#475569;">Unsubscribe</a>
  </div>
</body></html>"""


async def send_daily_digest() -> Dict:
    """Send digest to all active subscribers."""
    if not settings.smtp_user or not settings.smtp_pass:
        logger.warning("SMTP not configured — skipping email digest.")
        return {"sent": 0, "skipped": "SMTP not configured"}

    users_col = get_collection("users")
    news_col = get_collection("news")
    top10_col = get_collection("top10")
    trends_col = get_collection("trends")

    today = date.today().isoformat()
    top10_doc = await top10_col.find_one({"date": today}) or {}
    trends_doc = await trends_col.find_one({"date": today}) or {}

    cursor = news_col.find({"processed": True}).sort("published_at", -1).limit(15)
    headlines = await cursor.to_list(length=15)

    cursor = users_col.find({"active": True})
    subscribers = await cursor.to_list(length=1000)

    if not subscribers:
        logger.info("No active subscribers")
        return {"sent": 0, "skipped": "no subscribers"}

    date_str = datetime.now().strftime("%A, %B %d, %Y")
    sent, errors = 0, 0

    try:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_pass)

        for user in subscribers:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"📰 Daily News Intelligence — {date_str}"
                msg["From"] = settings.from_email
                msg["To"] = user["email"]
                html = _build_html(top10_doc.get("items", []), headlines, trends_doc, date_str, user["email"])
                msg.attach(MIMEText(html, "html"))
                server.sendmail(settings.smtp_user, user["email"], msg.as_string())
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send to {user['email']}: {e}")
                errors += 1
        server.quit()
    except Exception as e:
        logger.error(f"SMTP connection failed: {e}")
        return {"sent": 0, "error": str(e)}

    logger.info(f"✅ Email digest: sent={sent}, errors={errors}")
    return {"sent": sent, "errors": errors}
