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
                item = {
                    "object_a": first["name"],
                    "object_b": second["name"],
                    "position_difference_km": position_difference,
                    "velocity_difference_km_s": velocity_difference,
                }
                if first.get("catalog_id") is not None:
                    item["catalog_id_a"] = str(first["catalog_id"])
                if second.get("catalog_id") is not None:
                    item["catalog_id_b"] = str(second["catalog_id"])
                duplicates.append(item)
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
            "catalog_id_a": first[1][2:7].strip(),
            "catalog_id_b": second[1][2:7].strip(),
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
                "catalog_id": record[1][2:7].strip(),
                "position": position,
                "velocity": velocity,
            })

        duplicates = find_duplicate_states(
            states, tolerance_km, velocity_tolerance_km_s
        )
        duplicate_ids = {
            frozenset((
                item.get("catalog_id_a", item["object_a"]),
                item.get("catalog_id_b", item["object_b"]),
            )): item
            for item in duplicates
        }

        for key, result in list(still_duplicate.items()):
            ids = frozenset((
                records[key[0]][1][2:7].strip(),
                records[key[1]][1][2:7].strip(),
            ))
            item = duplicate_ids.get(ids)
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

def classify_tle_epoch(epoch, reference_time, max_age_hours=6.0):
    """Classify a TLE epoch without silently discarding its record."""
    if (
        isinstance(max_age_hours, bool)
        or not isinstance(max_age_hours, (int, float))
        or not math.isfinite(max_age_hours)
        or max_age_hours < 0
    ):
        raise ValueError("max_age_hours must be finite and non-negative.")

    age = tle_age_hours(epoch, reference_time)
    if age < 0:
        return "future_epoch"
    if age > max_age_hours:
        return "stale"
    return "fresh"

def tle_epoch_datetime(line1):
    'Parse the UTC epoch from columns 19-32 of a TLE line 1.'
    if not isinstance(line1, str) or len(line1) < 32 or not line1.startswith("1 "):
        raise ValueError("Invalid TLE line 1: missing epoch field.")
    field = line1[18:32]
    if len(field) != 14 or not field[:2].isdigit():
        raise ValueError("Invalid TLE epoch field.")
    try:
        day_of_year = float(field[2:])
    except ValueError as exc:
        raise ValueError("Invalid TLE epoch day-of-year.") from exc

    short_year = int(field[:2])
    year = 2000 + short_year if short_year < 57 else 1900 + short_year
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    next_year_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    days_in_year = (next_year_start - year_start).days
    if not math.isfinite(day_of_year) or not (1.0 <= day_of_year < days_in_year + 1):
        raise ValueError("TLE epoch day-of-year is outside the calendar year.")
    return year_start + timedelta(days=day_of_year - 1.0)


def filter_fresh_tle_records(records, reference_time, max_age_hours=6.0):
    'Return eligible records and a diagnostic report for every input TLE.'
    eligible = []
    report = []
    for name, line1, line2 in records:
        try:
            epoch = tle_epoch_datetime(line1)
            age_hours = tle_age_hours(epoch, reference_time)
            status = classify_tle_epoch(epoch, reference_time, max_age_hours)
        except (TypeError, ValueError, IndexError, OverflowError):
            age_hours = None
            status = "invalid_epoch"

        report.append({
            "object": name,
            "age_hours": age_hours,
            "status": status,
        })
        if status == "fresh":
            eligible.append((name, line1, line2))
    return eligible, report




def omm_epoch_datetime(epoch_value, time_system="UTC"):
    """Parse an OMM EPOCH; naive timestamps are UTC only when declared UTC."""
    if not isinstance(epoch_value, str) or not epoch_value.strip():
        raise ValueError("OMM EPOCH must be a non-empty ISO-8601 string.")

    value = epoch_value.strip()
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if str(time_system).strip().upper() != "UTC":
            raise ValueError("OMM EPOCH has no UTC offset and TIME_SYSTEM is not UTC.")
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def filter_fresh_omm_records(records, reference_time, max_age_hours=6.0):
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must be timezone-aware.")
    if (isinstance(max_age_hours, bool) or
            not isinstance(max_age_hours, (int, float)) or
            not math.isfinite(max_age_hours) or max_age_hours < 0):
        raise ValueError("max_age_hours must be finite and non-negative.")
    eligible, report = [], []
    for record in records:
        try:
            time_system = record.get("fields", {}).get("TIME_SYSTEM", "UTC")
            epoch = omm_epoch_datetime(record["epoch"], time_system)
            age = tle_age_hours(epoch, reference_time)
            status = "future_epoch" if age < 0 else "stale" if age > max_age_hours else "fresh"
        except (KeyError, TypeError, ValueError, OverflowError):
            age, status = None, "invalid_epoch"
        report.append({
            "object": record.get("name", "UNKNOWN"),
            "catalog_id": str(record.get("norad_id", "")),
            "age_hours": age,
            "status": status,
        })
        if status == "fresh":
            eligible.append(record)
    return eligible, report
