from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    """Return current time in Beijing timezone (UTC+8)."""
    return datetime.now(BEIJING_TZ)
