import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sgp4.api import jday
from scripts.fetch_satellites import parse_omm_xml
from scripts.screen_approaches import propagate_omm_records
from skytrace.time_window import filter_fresh_omm_records, find_duplicate_states


def propagate_at(records, when):
    return propagate_omm_records(records, when)



def duplicate_state_pairs(states):
    """Return duplicate OMM state pairs keyed by stable catalog IDs."""
    duplicates = {}
    for item in find_duplicate_states(states):
        if item.get("catalog_id_a") is None or item.get("catalog_id_b") is None:
            continue
        key = tuple(sorted((str(item["catalog_id_a"]), str(item["catalog_id_b"]))))
        duplicates[key] = item
    return duplicates


def persistent_duplicate_state_pairs(samples):
    """Return pairs whose position and velocity remain duplicates at every sample."""
    persistent = None
    details = {}
    for states in samples:
        current = duplicate_state_pairs(states)
        details.update(current)
        keys = set(current)
        persistent = keys if persistent is None else persistent.intersection(keys)
    return {key: details[key] for key in (persistent or set())}


def sample_window_times(start, end, step_seconds):
    """Return timestamps including the exact requested end."""
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")
    if end < start:
        raise ValueError("end must not precede start")
    times = []
    current = start
    step = timedelta(seconds=step_seconds)
    while current <= end:
        times.append(current)
        current += step
    if not times or times[-1] != end:
        times.append(end)
    return times


def main():
    parser = argparse.ArgumentParser(description="SKYTRACE OMM close-approach screening")
    parser.add_argument("--data-file", required=True)
    parser.add_argument("--hours", type=float, default=0)
    parser.add_argument("--step-seconds", type=float, default=60)
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--max-age-hours", type=float, default=6)
    parser.add_argument("--start", default=None)
    args = parser.parse_args()

    if not 0 <= args.hours <= 24:
        parser.error("--hours must be between 0 and 24")
    if not 10 <= args.step_seconds <= 600:
        parser.error("--step-seconds must be between 10 and 600")
    if args.top < 1 or not 0.1 <= args.max_age_hours <= 72:
        parser.error("Invalid top or maximum age setting")

    path = Path(args.data_file)
    records = parse_omm_xml(path.read_text(encoding="utf-8"))
    start = (
        datetime.fromisoformat(args.start.replace("Z", "+00:00"))
        if args.start else datetime.now(timezone.utc)
    )
    if start.tzinfo is None or start.utcoffset() is None:
        parser.error("--start must include a timezone")

    eligible, report = filter_fresh_omm_records(
        records, start, args.max_age_hours
    )

    counts = {
        status: sum(item["status"] == status for item in report)
        for status in ("fresh", "stale", "future_epoch", "invalid_epoch")
    }

    if len(eligible) < 2:
        raise RuntimeError(
            "OMM screening stopped: fewer than two fresh records. "
            + json.dumps(counts)
        )

    results = []
    duplicate_flags = []
    pair_minima = {}

    if args.hours == 0:
        states = propagate_at(eligible, start)
        if len(states) < 2:
            raise RuntimeError("Fewer than two OMM objects propagated.")

        duplicates = duplicate_state_pairs(states)
        for item in duplicates.values():
            duplicate_flags.append({
                "type": "duplicate_state",
                **item,
                "classification": "data_quality_flag_not_collision_alert",
            })

        for i, first in enumerate(states):
            for second in states[i + 1:]:
                key = tuple(sorted((str(first["catalog_id"]), str(second["catalog_id"]))))
                if key in duplicates:
                    continue
                distance = math.dist(first["position"], second["position"])
                results.append({
                    "object_a": first["name"],
                    "catalog_id_a": first["catalog_id"],
                    "object_b": second["name"],
                    "catalog_id_b": second["catalog_id"],
                    "separation_km": distance,
                    "time_utc": start.isoformat(),
                    "method": "instantaneous OMM SGP4 state separation",
                })

        results.sort(key=lambda item: item["separation_km"])
        summary = {
            "objects_propagated": len(states),
            "pairs_evaluated": len(states) * (len(states) - 1) // 2,
            "duplicate_state_pairs": len(duplicates),
            "results_returned": min(args.top, len(results)),
        }
    else:
        end = start + timedelta(hours=args.hours)
        sample_times = sample_window_times(start, end, args.step_seconds)
        sample_count = 0
        pair_minima = {}
        evaluated_pair_keys = set()
        duplicate_samples = []

        for current in sample_times:
            states = propagate_at(eligible, current)
            sample_count += 1
            duplicate_samples.append(states)

            for i, first in enumerate(states):
                for second in states[i + 1:]:
                    key = tuple(sorted((str(first["catalog_id"]), str(second["catalog_id"]))))
                    evaluated_pair_keys.add(key)
                    distance = math.dist(first["position"], second["position"])

                    previous = pair_minima.get(key)
                    if previous is None or distance < previous["separation_km"]:
                        pair_minima[key] = {
                            "object_a": first["name"],
                            "catalog_id_a": first["catalog_id"],
                            "object_b": second["name"],
                            "catalog_id_b": second["catalog_id"],
                            "separation_km": distance,
                            "time_utc": current.isoformat(),
                        }

        persistent_duplicates = persistent_duplicate_state_pairs(duplicate_samples)
        for item in persistent_duplicates.values():
            duplicate_flags.append({
                "type": "duplicate_state",
                **item,
                "samples_evaluated": sample_count,
                "classification": "data_quality_flag_not_collision_alert",
            })

        for key in persistent_duplicates:
            pair_minima.pop(key, None)

        results = sorted(
            pair_minima.values(), key=lambda item: item["separation_km"]
        )
        for item in results:
            item["samples_evaluated"] = sample_count
            item["method"] = "sampled OMM SGP4 minimum separation"

        summary = {
            "objects_input": len(eligible),
            "samples_evaluated": sample_count,
            "pairs_evaluated": len(evaluated_pair_keys),
            "duplicate_state_pairs": len(persistent_duplicates),
            "results_returned": min(args.top, len(results)),
        }

    valid_ages = [
        item["age_hours"] for item in report
        if isinstance(item.get("age_hours"), (int, float))
        and math.isfinite(item["age_hours"])
    ]
    youngest_age_hours = min(valid_ages) if valid_ages else None
    oldest_age_hours = max(valid_ages) if valid_ages else None

    payload = {
        "schema_version": "1.0",
        "product": "SKYTRACE",
        "data_file": path.name,
        "element_format": "OMM-XML",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "screening": {
            "mode": "instantaneous" if args.hours == 0 else "sampled_window",
            "start_utc": start.isoformat(),
            "hours": args.hours,
            "step_seconds": args.step_seconds if args.hours else None,
            "input_objects": len(records),
            "eligible_objects": len(eligible),
            "excluded_objects": len(records) - len(eligible),
        },
        "tle_freshness": {
            "max_age_hours": args.max_age_hours,
            "youngest_age_hours": youngest_age_hours,
            "oldest_age_hours": oldest_age_hours,
            "records": report,
            "fresh_records": counts["fresh"],
            "stale_records": counts["stale"],
            "future_epoch_records": counts["future_epoch"],
            "invalid_epoch_records": counts["invalid_epoch"],
        },
        "data_quality_flags": duplicate_flags,
        "results": results[:args.top],
        "summary": summary,
        "limitations": [
            "OMM epoch age does not quantify orbital uncertainty.",
            "Sampled minima are not guaranteed continuous-time minima.",
            "No collision probability or operational risk assessment is performed.",
            "Duplicate states are data-quality flags, not collision alerts.",
        ],
    }

    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
