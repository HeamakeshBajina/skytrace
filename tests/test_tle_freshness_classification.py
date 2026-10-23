from datetime import datetime, timedelta, timezone

import pytest

from skytrace.time_window import classify_tle_epoch


def test_tle_within_six_hours_is_fresh():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    assert classify_tle_epoch(now - timedelta(hours=5), now) == "fresh"


def test_tle_older_than_six_hours_is_stale():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    assert classify_tle_epoch(now - timedelta(hours=7), now) == "stale"


def test_future_tle_epoch_is_flagged():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    assert classify_tle_epoch(now + timedelta(minutes=5), now) == "future_epoch"


def test_tle_exactly_six_hours_old_is_fresh():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    assert classify_tle_epoch(now - timedelta(hours=6), now) == "fresh"


def test_invalid_max_age_is_rejected():
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        classify_tle_epoch(now, now, max_age_hours=-1)
