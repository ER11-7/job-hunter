from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def within_last_hour(timestamp: datetime) -> bool:
    return utc_now() - timestamp <= timedelta(hours=1)


def friendly_timestamp(timestamp: datetime) -> str:
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M %Z")
