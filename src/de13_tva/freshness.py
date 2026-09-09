"""Freshness helpers for stored VIES verdicts."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def freshness_days(checked_at: datetime | str, now: datetime | None = None) -> int:
    reference = now or datetime.now(UTC)
    return max((reference - parse_datetime(checked_at)).days, 0)


def is_fresh(
    checked_at: datetime | str,
    *,
    max_age_days: int,
    now: datetime | None = None,
) -> bool:
    return freshness_days(checked_at, now) <= max_age_days
