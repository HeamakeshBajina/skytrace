from scripts.screen_omm import duplicate_state_pairs, persistent_duplicate_state_pairs, sample_window_times


def state(name, catalog_id, position=(7000.0, 0.0, 0.0),
          velocity=(0.0, 7.5, 0.0)):
    return {
        "name": name,
        "catalog_id": catalog_id,
        "position": position,
        "velocity": velocity,
    }


def test_omm_identical_position_and_velocity_are_detected():
    result = duplicate_state_pairs([
        state("A", "11111"),
        state("B", "22222"),
    ])
    assert len(result) == 1
    assert ("11111", "22222") in result


def test_omm_same_position_different_velocity_is_not_duplicate():
    result = duplicate_state_pairs([
        state("A", "11111"),
        state("B", "22222", velocity=(0.0, 7.6, 0.0)),
    ])
    assert result == {}


def test_omm_duplicate_must_persist_across_all_samples():
    samples = [
        [state("A", "11111"), state("B", "22222")],
        [state("A", "11111"), state("B", "22222")],
    ]
    assert len(persistent_duplicate_state_pairs(samples)) == 1


def test_omm_transient_duplicate_is_not_persistent():
    samples = [
        [state("A", "11111"), state("B", "22222")],
        [state("A", "11111"), state("B", "22222",
                                     position=(7001.0, 0.0, 0.0))],
    ]
    assert persistent_duplicate_state_pairs(samples) == {}


def test_sample_window_includes_non_aligned_end_time():
    from datetime import datetime, timedelta, timezone
    start = datetime(2026, 11, 6, tzinfo=timezone.utc)
    end = start + timedelta(seconds=125)
    samples = sample_window_times(start, end, 60)
    assert samples == [
        start, start + timedelta(seconds=60),
        start + timedelta(seconds=120), end
    ]


def test_sample_window_does_not_duplicate_aligned_end_time():
    from datetime import datetime, timedelta, timezone
    start = datetime(2026, 11, 6, tzinfo=timezone.utc)
    end = start + timedelta(seconds=120)
    samples = sample_window_times(start, end, 60)
    assert samples == [
        start, start + timedelta(seconds=60), end
    ]
