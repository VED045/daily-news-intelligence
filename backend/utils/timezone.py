from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

def now_ist():
    """Return the current time in IST."""
    return datetime.now(IST)

def get_today_range_ist():
    """Return a tuple of (start, end) for 'today' in IST."""
    now = now_ist()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end

def ist_to_utc(dt):
    """Convert an IST datetime to UTC."""
    return dt.astimezone(pytz.UTC)
