from datetime import datetime, timezone, timedelta
import math
import pytest

from skytrace.time_window import sampled_minimum_separation

ISS = (
    "ISS",
    "1 25544U 98067A   21275.51005787  .00001490  00000-0  33225-4 0  9993",
    "2 25544  51.6442 208.9163 0003886  121.2047  319.9222 15.48815329302845",
)


def test_sampled_minimum_has_expected_fields_and_finite_distance():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    end = start + timedelta(minutes=3)
    result = sampled_minimum_separation(ISS, ISS, start, end, 60)

    assert result["object_a"] == "ISS"
    assert result["object_b"] == "ISS"
    assert result["time"] == start
    assert result["separation_km"] == pytest.approx(0.0, abs=1e-9)
    assert result["samples_evaluated"] == 4
    assert math.isfinite(result["separation_km"])


def test_end_time_is_included_when_step_does_not_divide_window():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    end = start + timedelta(seconds=125)
    result = sampled_minimum_separation(ISS, ISS, start, end, 60)
    assert result["samples_evaluated"] == 4
    assert result["time"] <= end


@pytest.mark.parametrize("step", [0, -1, float("inf"), float("nan"), True])
def test_invalid_step_is_rejected(step):
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    with pytest.raises((ValueError, TypeError)):
        sampled_minimum_separation(ISS, ISS, start, start, step)


def test_naive_datetime_is_rejected():
    start = datetime(2021, 10, 2, 12, 14, 29)
    with pytest.raises(ValueError):
        sampled_minimum_separation(ISS, ISS, start, start + timedelta(minutes=1))


def test_reversed_time_window_is_rejected():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        sampled_minimum_separation(ISS, ISS, start + timedelta(minutes=1), start)

def test_zero_duration_window_evaluates_one_sample():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    result = sampled_minimum_separation(ISS, ISS, start, start, 60)
    assert result["samples_evaluated"] == 1
    assert result["time"] == start


def test_window_shorter_than_step_evaluates_both_endpoints():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    end = start + timedelta(seconds=20)
    result = sampled_minimum_separation(ISS, ISS, start, end, 60)
    assert result["samples_evaluated"] == 2
    assert result["time"] == start
