"""Propagate the ISS (ZARYA) from the latest locally saved station TLE."""
import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
import sys

from sgp4.api import Satrec, jday
from sgp4.conveniences import sat_epoch_datetime


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp that includes a timezone."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Use ISO-8601, e.g. 2026-10-22T12:00:00Z"
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            "Timestamp must include Z or a UTC offset."
        )
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--time",
        type=parse_utc,
        default=None,
        help="Propagation time in ISO-8601 UTC or with an explicit UTC offset.",
    )
    args = parser.parse_args()

    files = sorted(
        Path("data/raw").glob("stations_*.tle"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print(
            "ERROR: No stations_*.tle files found in data/raw. "
            "Run scripts/fetch_satellites.py first.",
            file=sys.stderr,
        )
        return 1

    records = []
    lines = files[0].read_text(encoding="utf-8").splitlines()
    for index in range(0, len(lines) - 2, 3):
        name, line1, line2 = lines[index:index + 3]
        if line1[2:7].strip() == "25544" and line2[2:7].strip() == "25544":
            records.append((name, line1, line2))
            break

    if not records:
        print("ERROR: ISS (NORAD 25544) not found in the latest TLE file.", file=sys.stderr)
        return 1

    name, line1, line2 = records[0]
    try:
        satellite = Satrec.twoline2rv(line1, line2)
    except Exception as exc:
        print(f"ERROR: Could not parse ISS TLE: {exc}", file=sys.stderr)
        return 1

    now = args.time or datetime.now(timezone.utc)
    jd, fr = jday(
        now.year, now.month, now.day,
        now.hour, now.minute,
        now.second + now.microsecond / 1_000_000,
    )
    error, position, velocity = satellite.sgp4(jd, fr)

    print("=== SKYTRACE: SGP4 PROPAGATION ===")
    print(f"Data file: {files[0]}")
    print(f"Object: {name}")
    print(f"NORAD ID: {line1[2:7].strip()}")
    print(f"TLE epoch (UTC): {sat_epoch_datetime(satellite).isoformat()}")
    print(f"Requested time (UTC): {now.isoformat()}")

    if error:
        print(f"ERROR: SGP4 propagation failed; error code: {error}", file=sys.stderr)
        return 1
    if not all(math.isfinite(value) for value in (*position, *velocity)):
        print("ERROR: SGP4 returned a non-finite state.", file=sys.stderr)
        return 1

    x, y, z = position
    vx, vy, vz = velocity
    radius = math.dist((0.0, 0.0, 0.0), position)
    speed = math.dist((0.0, 0.0, 0.0), velocity)

    print("\nTEME position (km):")
    print(f"  x = {x:,.3f}")
    print(f"  y = {y:,.3f}")
    print(f"  z = {z:,.3f}")
    print("\nTEME velocity (km/s):")
    print(f"  vx = {vx:.6f}")
    print(f"  vy = {vy:.6f}")
    print(f"  vz = {vz:.6f}")
    print(f"\nGeocentric radius: {radius:,.3f} km")
    print(f"Speed: {speed:.6f} km/s")
    print("\nNOTE: Position is in TEME coordinates, not latitude/longitude.")
    print("This is a propagated estimate from the TLE, not a live measurement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
