import pytest

from skytrace.time_window import find_duplicate_states


def test_identical_states_are_detected():
    states = [
        {"name": "ISS", "position": (1.0, 2.0, 3.0), "velocity": (4.0, 5.0, 6.0)},
        {"name": "DOCKED", "position": (1.0, 2.0, 3.0), "velocity": (4.0, 5.0, 6.0)},
        {"name": "OTHER", "position": (10.0, 20.0, 30.0), "velocity": (1.0, 1.0, 1.0)},
    ]
    result = find_duplicate_states(states)
    assert len(result) == 1
    assert result[0]["object_a"] == "ISS"
    assert result[0]["object_b"] == "DOCKED"


def test_different_velocities_are_not_duplicate_states():
    states = [
        {"name": "A", "position": (1.0, 2.0, 3.0), "velocity": (4.0, 5.0, 6.0)},
        {"name": "B", "position": (1.0, 2.0, 3.0), "velocity": (4.1, 5.0, 6.0)},
    ]
    assert find_duplicate_states(states) == []


def test_invalid_tolerance_is_rejected():
    state = [{"name": "A", "position": (0, 0, 0), "velocity": (0, 0, 0)}]
    with pytest.raises(ValueError):
        find_duplicate_states(state, tolerance_km=-1)
