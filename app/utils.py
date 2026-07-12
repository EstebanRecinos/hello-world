from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; normalize anything read back to UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
