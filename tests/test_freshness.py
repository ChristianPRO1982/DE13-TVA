from datetime import UTC, datetime, timedelta

from de13_tva.freshness import freshness_days, is_fresh, parse_datetime


def test_parse_datetime_accepts_datetime_and_string():
    aware = datetime(2026, 9, 9, tzinfo=UTC)

    assert parse_datetime(aware) == aware
    assert parse_datetime("2026-09-09T00:00:00").tzinfo == UTC
    assert parse_datetime("2026-09-09T12:00:00+00:00").tzinfo == UTC


def test_freshness_days_never_negative():
    now = datetime(2026, 9, 9, tzinfo=UTC)

    assert freshness_days(now - timedelta(days=2), now) == 2
    assert freshness_days(now + timedelta(days=2), now) == 0


def test_is_fresh_uses_max_age_days():
    now = datetime(2026, 9, 9, tzinfo=UTC)

    assert is_fresh(now - timedelta(days=30), max_age_days=30, now=now)
    assert not is_fresh(now - timedelta(days=31), max_age_days=30, now=now)
