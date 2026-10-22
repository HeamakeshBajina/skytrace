from datetime import datetime, timedelta, timezone

from skytrace.time_window import find_duplicate_pairs_over_window

ISS = (
    "ISS",
    "1 25544U 98067A   21275.51005787  .00001490  00000-0  33225-4 0  9993",
    "2 25544  51.6442 208.9163 0003886  121.2047  319.9222 15.48815329302845",
)


def test_identical_record_stays_duplicate_across_window():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    other = ("ISS-copy", ISS[1], ISS[2])
    result = find_duplicate_pairs_over_window(
        [ISS, other], start, start + timedelta(seconds=125), 60
    )
    assert len(result) == 1
    assert result[0]["samples_evaluated"] == 4
    assert result[0]["max_position_difference_km"] == 0.0
    assert result[0]["max_velocity_difference_km_s"] == 0.0


def test_different_orbits_are_not_reported_as_duplicate():
    start = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    other = (
        "OTHER",
        "1 00005U 58002B   21274.99768519  .00000023  00000-0  28098-4 0  9990",
        "2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413667",
    )
    result = find_duplicate_pairs_over_window(
        [ISS, other], start, start + timedelta(seconds=60), 60
    )
    assert result == []
