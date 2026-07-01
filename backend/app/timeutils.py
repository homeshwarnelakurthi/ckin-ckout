"""Period boundary helpers.

Timestamps are stored in UTC; "today", "this week" and "this month" are only
meaningful in the workplace's local timezone. These helpers compute the local
period boundaries and return them as UTC instants suitable for querying.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _local_now(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def day_bounds_utc(tz_name: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    local = (now.astimezone(tz) if now else _local_now(tz_name))
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def week_bounds_utc(tz_name: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Week starts Monday, local time."""
    tz = ZoneInfo(tz_name)
    local = (now.astimezone(tz) if now else _local_now(tz_name))
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=local.weekday()
    )
    end_local = start_local + timedelta(days=7)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def month_bounds_utc(tz_name: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    local = (now.astimezone(tz) if now else _local_now(tz_name))
    start_local = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_local.month == 12:
        end_local = start_local.replace(year=start_local.year + 1, month=1)
    else:
        end_local = start_local.replace(month=start_local.month + 1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
