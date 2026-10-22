"""Preliminary sampled satellite separation screening using SGP4.

This module finds the minimum separation among sampled times only.
It is not a validated conjunction assessment or collision probability model.
"""
from datetime import datetime, timedelta, timezone
import math

from sgp4.api import Satrec, jday


def _propagate(satellite, when):
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("All datetimes must be timezone-aware.")

    when = when.astimezone(timezone.utc)
    jd, fr = jday(
        when.year, when.month, when.day,
        when.hour, when.minute,
        when.second + when.microsecond / 1_000_000,
    )
    error, position, velocity = satellite.sgp4(jd, fr)
    if error != 0:
        raise ValueError(f"SGP4 propagation failed with code {error}.")
    if not all(math.isfinite(x) for x in (*position, *velocity)):
        raise ValueError("SGP4 returned a non-finite state.")
    return tuple(position), tuple(velocity)


def sampled_minimum_separation(
    record_a,
    record_b,
    start,
    end,
    step_seconds=60.0,
):
    """Return the closest sampled separation between two TLE records.

    Each record is (name, line1, line2). Positions and separation use km.
    The end time is included even when the interval is not divisible by step.
    """
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware.")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must be timezone-aware.")
    if end < start:
        raise ValueError("end must be at or after start.")
    if isinstance(step_seconds, bool) or not isinstance(step_seconds, (int, float)):
        raise TypeError("step_seconds must be a real number.")
    if not math.isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("step_seconds must be finite and positive.")

    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    sat_a = Satrec.twoline2rv(record_a[1], record_a[2])
    sat_b = Satrec.twoline2rv(record_b[1], record_b[2])

    best = None
    current = start
    while current < end:
        pos_a, _ = _propagate(sat_a, current)
        pos_b, _ = _propagate(sat_b, current)
        distance = math.dist(pos_a, pos_b)
        if best is None or distance < best["separation_km"]:
            best = {
                "time": current,
                "separation_km": distance,
                "object_a": record_a[0],
                "object_b": record_b[0],
            }
        current += timedelta(seconds=step_seconds)

    # Always evaluate the exact end time.
    pos_a, _ = _propagate(sat_a, end)
    pos_b, _ = _propagate(sat_b, end)
    distance = math.dist(pos_a, pos_b)
    if best is None or distance < best["separation_km"]:
        best = {
            "time": end,
            "separation_km": distance,
            "object_a": record_a[0],
            "object_b": record_b[0],
        }

    return {
        **best,
        "samples_evaluated": int((end - start).total_seconds() // step_seconds) + 1
        if (end - start).total_seconds() % step_seconds == 0
        else int((end - start).total_seconds() // step_seconds) + 2,
        "method": "sampled minimum; not a continuous-time minimum guarantee",
    }


def find_duplicate_states(states, tolerance_km=1e-6, velocity_tolerance_km_s=1e-9):
    """Return pairs whose propagated positions and velocities are nearly identical.

    Each state must contain name, position, and velocity fields.
    This detects duplicate numerical states, not collision risk.
    """
    if not math.isfinite(tolerance_km) or tolerance_km < 0:
        raise ValueError("tolerance_km must be finite and non-negative.")
    if not math.isfinite(velocity_tolerance_km_s) or velocity_tolerance_km_s < 0:
        raise ValueError(
            "velocity_tolerance_km_s must be finite and non-negative."
        )

    duplicates = []
    for index, first in enumerate(states):
        for second in states[index + 1:]:
            position_difference = math.dist(
                first["position"], second["position"]
            )
            velocity_difference = math.dist(
                first["velocity"], second["velocity"]
            )
            if (
                position_difference <= tolerance_km
                and velocity_difference <= velocity_tolerance_km_s
            ):
                duplicates.append({
                    "object_a": first["name"],
                    "object_b": second["name"],
                    "position_difference_km": position_difference,
                    "velocity_difference_km_s": velocity_difference,
                })
    return duplicates


def find_duplicate_pairs_over_window(
    records, start, end, step_seconds=60.0,
    tolerance_km=1e-6, velocity_tolerance_km_s=1e-9,
):
    """Find record pairs whose propagated states stay nearly identical at
    every sampled timestamp in the requested window.

    This is a numerical data-quality diagnostic, not a collision assessment.
    The end timestamp is always evaluated.
    """
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware.")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must be timezone-aware.")
    if end < start:
        raise ValueError("end must be at or after start.")
    if isinstance(step_seconds, bool) or not isinstance(step_seconds, (int, float)):
        raise TypeError("step_seconds must be a real number.")
    if not math.isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("step_seconds must be finite and positive.")
    if not math.isfinite(tolerance_km) or tolerance_km < 0:
        raise ValueError("tolerance_km must be finite and non-negative.")
    if (
        not math.isfinite(velocity_tolerance_km_s)
        or velocity_tolerance_km_s < 0
    ):
        raise ValueError(
            "velocity_tolerance_km_s must be finite and non-negative."
        )

    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    satellites = [
        (record, Satrec.twoline2rv(record[1], record[2]))
        for record in records
    ]
    still_duplicate = {
        (i, j): {
            "object_a": first[0],
            "object_b": second[0],
            "max_position_difference_km": 0.0,
            "max_velocity_difference_km_s": 0.0,
            "samples_evaluated": 0,
        }
        for i, (first, _) in enumerate(satellites)
        for j, (second, _) in enumerate(satellites[i + 1:], start=i + 1)
    }

    current = start
    sample_count = 0
    while True:
        states = []
        for record, satellite in satellites:
            position, velocity = _propagate(satellite, current)
            states.append({
                "name": record[0],
                "position": position,
                "velocity": velocity,
            })

        duplicates = find_duplicate_states(
            states, tolerance_km, velocity_tolerance_km_s
        )
        duplicate_names = {
            frozenset((item["object_a"], item["object_b"])): item
            for item in duplicates
        }

        for key, result in list(still_duplicate.items()):
            names = frozenset((result["object_a"], result["object_b"]))
            item = duplicate_names.get(names)
            if item is None:
                del still_duplicate[key]
            else:
                result["max_position_difference_km"] = max(
                    result["max_position_difference_km"],
                    item["position_difference_km"],
                )
                result["max_velocity_difference_km_s"] = max(
                    result["max_velocity_difference_km_s"],
                    item["velocity_difference_km_s"],
                )
                result["samples_evaluated"] += 1

        sample_count += 1
        if current >= end:
            break
        current = min(current + timedelta(seconds=step_seconds), end)

    return list(still_duplicate.values())


def tle_age_hours(epoch, reference_time):
    """Return TLE age in hours at a timezone-aware reference time.

    Negative values indicate that the TLE epoch is later than the reference
    time; callers should not label those records as stale.
    """
    if epoch.tzinfo is None or epoch.utcoffset() is None:
        raise ValueError("epoch must be timezone-aware.")
    if (
        reference_time.tzinfo is None
        or reference_time.utcoffset() is None
    ):
        raise ValueError("reference_time must be timezone-aware.")
    return (
        reference_time.astimezone(timezone.utc)
        - epoch.astimezone(timezone.utc)
    ).total_seconds() / 3600.0
