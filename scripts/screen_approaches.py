"""Preliminary satellite close-approach screening from TLE data."""
import argparse
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path

from sgp4.api import Satrec, jday
from skytrace.time_window import (
    find_duplicate_pairs_over_window,
    find_duplicate_states,
    sampled_minimum_separation,
    tle_age_hours,
)


def propagate_records(records, when):
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("Propagation time must be timezone-aware.")
    when = when.astimezone(timezone.utc)
    jd, fr = jday(
        when.year, when.month, when.day,
        when.hour, when.minute,
        when.second + when.microsecond / 1_000_000,
    )
    states = []
    for name, line1, line2 in records:
        satellite = Satrec.twoline2rv(line1, line2)
        error, position, velocity = satellite.sgp4(jd, fr)
        if error != 0 or not all(
            math.isfinite(value) for value in (*position, *velocity)
        ):
            continue
        states.append({
            "name": name,
            "catalog_id": line1[2:7].strip(),
            "line1": line1,
            "line2": line2,
            "position": tuple(position),
            "velocity": tuple(velocity),
            "epoch": satellite.jdsatepoch + satellite.jdsatepochF,
        })
    return states



def identical_state_pairs(states, tolerance_km=1e-6):
    """Return (distance_km, object_a, object_b) for nearly identical positions."""
    if not math.isfinite(tolerance_km) or tolerance_km < 0:
        raise ValueError("tolerance_km must be finite and non-negative.")

    flagged = []
    for index, first in enumerate(states):
        for second in states[index + 1:]:
            distance = math.dist(first["position"], second["position"])
            if distance <= tolerance_km:
                flagged.append((distance, first, second))
    return flagged
def load_latest_records():
    files = sorted(
        Path("data/raw").glob("stations_*.tle"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError("Run scripts/fetch_satellites.py first.")
    lines = [
        line.strip()
        for line in files[0].read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(lines) % 3:
        raise ValueError("TLE file does not contain complete three-line records.")
    records = []
    for index in range(0, len(lines), 3):
        name, line1, line2 = lines[index:index + 3]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            raise ValueError(f"Invalid TLE structure near {name!r}.")
        if line1[2:7] != line2[2:7]:
            raise ValueError(f"Catalog ID mismatch for {name!r}.")
        records.append((name, line1, line2))
    return files[0], records


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Use ISO-8601, e.g. 2026-10-22T00:00:00Z"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("Timestamp must include Z or a UTC offset.")
    return parsed.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=0.0)
    parser.add_argument("--step-seconds", type=float, default=60.0)
    parser.add_argument("--start", type=parse_utc, default=None)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    if not math.isfinite(args.hours) or args.hours < 0:
        parser.error("--hours must be finite and non-negative.")
    if not math.isfinite(args.step_seconds) or args.step_seconds <= 0:
        parser.error("--step-seconds must be finite and positive.")
    if args.top < 1:
        parser.error("--top must be at least 1.")

    data_file, records = load_latest_records()
    start = args.start or datetime.now(timezone.utc)
    print("\n=== SKYTRACE: PRELIMINARY CLOSE-APPROACH SCREEN ===")
    print(f"Data file: {data_file}")
    print(f"Input objects: {len(records)}")
    print(f"Start time (UTC): {start.isoformat()}")

    # Calculate each TLE epoch from its orbital elements, not file timestamps.
    ages = []
    future_epochs = []
    for name, line1, line2 in records:
        satellite = Satrec.twoline2rv(line1, line2)
        epoch_jd = satellite.jdsatepoch + satellite.jdsatepochF
        epoch_datetime = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(
            days=epoch_jd - 2451545.0
        )
        age_hours = tle_age_hours(epoch_datetime, start)
        ages.append((name, age_hours))
        if age_hours < 0:
            future_epochs.append((name, age_hours))

    if ages:
        age_values = [age for _, age in ages]
        print(
            "TLE age at screening start: "
            f"youngest={min(age_values):.2f} h, "
            f"oldest={max(age_values):.2f} h"
        )
        if future_epochs:
            print(
                "WARNING: TLE epoch is later than screening start for: "
                + ", ".join(name for name, _ in future_epochs)
            )
        else:
            print("TLE epoch check: all epochs are at or before screening start.")
    print("Freshness note: age alone does not quantify orbital uncertainty.")

    if args.hours == 0:
        states = propagate_records(records, start)
        if len(states) < 2:
            raise RuntimeError("Need at least two successfully propagated objects.")

        duplicates = find_duplicate_states(states)
        duplicate_keys = {
            frozenset((item["object_a"], item["object_b"]))
            for item in duplicates
        }

        print("Mode: instantaneous")
        print(f"Objects propagated: {len(states)}")
        print(f"Duplicate-state pairs flagged: {len(duplicates)}")
        if duplicates:
            print("\n=== DATA-QUALITY FLAGS - NOT COLLISION ALERTS ===")
            for item in duplicates:
                print(
                    f"{item['position_difference_km']:.9f} km; "
                    f"{item['velocity_difference_km_s']:.12f} km/s | "
                    f"{item['object_a']} <-> {item['object_b']}"
                )

        approaches = []
        for i, first in enumerate(states):
            for second in states[i + 1:]:
                if frozenset((first["name"], second["name"])) in duplicate_keys:
                    continue
                approaches.append((
                    math.dist(first["position"], second["position"]),
                    first, second,
                ))
        approaches.sort(key=lambda item: item[0])
        print(f"Pairs evaluated: {len(states) * (len(states) - 1) // 2}")
        print("\n=== CLOSEST NON-DUPLICATE PAIRS ===")
        for distance, first, second in approaches[:args.top]:
            print(
                f"{distance:10.3f} km | {first['name']} "
                f"[{first['catalog_id']}] <-> {second['name']} "
                f"[{second['catalog_id']}]"
            )
    else:
        end = start + timedelta(hours=args.hours)
        print("Mode: sampled time window")
        print(f"End time (UTC): {end.isoformat()}")
        print(f"Sampling interval: {args.step_seconds:g} seconds")

        # Exclude only pairs whose states remain numerically identical at
        # every sampled timestamp. This is a data-quality filter, not a
        # collision-risk classification.
        duplicates = find_duplicate_pairs_over_window(
            records, start, end, args.step_seconds
        )
        duplicate_keys = {
            frozenset((item["object_a"], item["object_b"]))
            for item in duplicates
        }
        print(f"Duplicate-state pairs across all samples: {len(duplicates)}")
        if duplicates:
            print("\n=== DATA-QUALITY FLAGS - NOT COLLISION ALERTS ===")
            for item in duplicates:
                print(
                    f"{item['object_a']} <-> {item['object_b']} | "
                    f"samples={item['samples_evaluated']} | "
                    f"max position difference="
                    f"{item['max_position_difference_km']:.9f} km"
                )

        results = []
        failures = 0
        for i, first in enumerate(records):
            for second in records[i + 1:]:
                if frozenset((first[0], second[0])) in duplicate_keys:
                    continue
                try:
                    results.append(sampled_minimum_separation(
                        first, second, start, end, args.step_seconds
                    ))
                except (ValueError, OverflowError) as exc:
                    failures += 1
                    print(f"WARNING: skipped {first[0]} / {second[0]}: {exc}")

        results.sort(key=lambda item: item["separation_km"])
        print(f"Non-duplicate pairs successfully screened: {len(results)}")
        print(f"Pairs skipped due to errors: {failures}")
        print("\n=== CLOSEST NON-DUPLICATE PAIRS ===")
        for item in results[:args.top]:
            print(
                f"{item['separation_km']:10.3f} km | "
                f"{item['time'].isoformat()} | "
                f"{item['object_a']} <-> {item['object_b']}"
            )

    print("\nLIMITATIONS:")
    print("- Duplicate states indicate matching numerical states, not collision risk.")
    print("- Sampled minima are not guaranteed continuous-time minima.")
    print("- No collision probability or operational risk assessment is performed.")
    print("- TLE age and orbital uncertainty require separate review.")


if __name__ == "__main__":
    main()
