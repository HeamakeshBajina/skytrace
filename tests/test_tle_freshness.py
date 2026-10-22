from datetime import datetime, timedelta, timezone

import pytest

from skytrace.time_window import tle_age_hours


def test_tle_age_is_reported_in_hours():
    epoch = datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc)
    reference = epoch + timedelta(hours=18)
    assert tle_age_hours(epoch, reference) == pytest.approx(18.0)


def test_future_epoch_returns_negative_age():
    reference = datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc)
    epoch = reference + timedelta(hours=2)
    assert tle_age_hours(epoch, reference) == pytest.approx(-2.0)


def test_naive_epoch_is_rejected():
    epoch = datetime(2026, 10, 21, 0, 0)
    reference = datetime(2026, 10, 21, 1, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        tle_age_hours(epoch, reference)


def test_naive_reference_time_is_rejected():
    epoch = datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc)
    reference = datetime(2026, 10, 21, 1, 0)
    with pytest.raises(ValueError):
        tle_age_hours(epoch, reference)
