import math
from datetime import datetime, timezone

from scripts.screen_approaches import (
    identical_state_pairs,
    propagate_records,
)

ISS_RECORD = (
    "ISS (ZARYA)",
    "1 25544U 98067A   21275.51005787  .00001490  00000-0  33225-4 0  9993",
    "2 25544  51.6442 208.9163 0003886  121.2047  319.9222 15.48815329302845",
)


def test_identical_positions_are_flagged():
    states = [
        {"name": "A", "catalog_id": "1", "position": (1.0, 2.0, 3.0)},
        {"name": "B", "catalog_id": "2", "position": (1.0, 2.0, 3.0)},
        {"name": "C", "catalog_id": "3", "position": (10.0, 20.0, 30.0)},
    ]
    flagged = identical_state_pairs(states)
    assert len(flagged) == 1
    assert flagged[0][0] == 0.0


def test_distinct_positions_are_not_flagged():
    states = [
        {"name": "A", "catalog_id": "1", "position": (0.0, 0.0, 0.0)},
        {"name": "B", "catalog_id": "2", "position": (1.0, 0.0, 0.0)},
    ]
    assert identical_state_pairs(states) == []


def test_fixed_tle_propagation_returns_finite_state():
    when = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    states = propagate_records([ISS_RECORD], when)

    assert len(states) == 1
    assert states[0]["catalog_id"] == "25544"
    assert all(math.isfinite(value) for value in states[0]["position"])
    assert all(math.isfinite(value) for value in states[0]["velocity"])


def test_empty_record_list_returns_no_states():
    when = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    assert propagate_records([], when) == []
