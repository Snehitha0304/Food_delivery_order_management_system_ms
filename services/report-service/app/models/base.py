from datetime import datetime, timezone
from sqlalchemy import Column, DateTime


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
