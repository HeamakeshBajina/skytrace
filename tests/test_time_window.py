from datetime import datetime, timezone, timedelta
import math
import pytest

from skytrace.time_window import (
    find_duplicate_pairs_over_window,
    find_duplicate_states,
    sampled_minimum_separation,
)

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


def test_duplicate_state_detection_uses_catalog_ids_not_names():
    states = [
        {
            "name": "REUSED NAME",
            "catalog_id": "11111",
            "position": (7000.0, 0.0, 0.0),
            "velocity": (0.0, 7.5, 0.0),
        },
        {
            "name": "REUSED NAME",
            "catalog_id": "22222",
            "position": (7000.0, 0.0, 0.0),
            "velocity": (0.0, 7.5, 0.0),
        },
        {
            "name": "OTHER OBJECT",
            "catalog_id": "33333",
            "position": (7001.0, 0.0, 0.0),
            "velocity": (0.0, 7.5, 0.0),
        },
    ]

    duplicates = find_duplicate_states(states)

    assert len(duplicates) == 1
    assert duplicates[0]["object_a"] == "REUSED NAME"
    assert duplicates[0]["object_b"] == "REUSED NAME"
    assert duplicates[0]["catalog_id_a"] == "11111"
    assert duplicates[0]["catalog_id_b"] == "22222"


def test_window_duplicate_detection_preserves_reused_names_and_catalog_ids():
    start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    first = (
        "REUSED NAME",
        "1 25544U 98067A   26294.04791053  .00009575  00000+0  18188-3 0  9996",
        "2 25544  51.6327  37.2623 0006759 289.5321  70.4938 15.48967427591263",
    )
    second_line1 = first[1][:2] + "25545" + first[1][7:]
    second_line1 = second_line1[:68] + str(
        sum(int(c) if c.isdigit() else 1 if c == "-" else 0 for c in second_line1[:68]) % 10
    )
    second_line2_base = first[2][:2] + "25545" + first[2][7:]
    second_line2_base = second_line2_base[:68]
    second_line2_base = second_line2_base[:43] + " 70.4938 " + second_line2_base[52:]
    second_line2 = second_line2_base[:68] + str(
        sum(int(c) if c.isdigit() else 1 if c == "-" else 0 for c in second_line2_base[:68]) % 10
    )
    records = [
        first,
        ("REUSED NAME", second_line1, second_line2),
    ]

    duplicates = find_duplicate_pairs_over_window(
        records, start, start + timedelta(seconds=60), 60
    )

    assert len(duplicates) == 1
    assert duplicates[0]["object_a"] == "REUSED NAME"
    assert duplicates[0]["object_b"] == "REUSED NAME"
    assert {duplicates[0]["catalog_id_a"], duplicates[0]["catalog_id_b"]} == {
        "25544", "25545"
    }
    assert duplicates[0]["samples_evaluated"] == 2