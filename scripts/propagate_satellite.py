import sys
from datetime import datetime, timezone
from pathlib import Path

from sgp4.api import Satrec, jday
from sgp4.conveniences import sat_epoch_datetime


def main() -> None:
    files = sorted(
        Path("data/raw").glob("stations_*.tle"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError("No TLE file found. Run fetch_satellites.py first.")

    lines = [line.strip() for line in files[0].read_text(encoding="utf-8-sig").splitlines()
             if line.strip()]
    records = [
        lines[i:i + 3]
        for i in range(0, len(lines), 3)
        if i + 2 < len(lines)
    ]

    chosen = next(
        (r for r in records if r[0].upper().startswith("ISS (ZARYA)")),
        None,
    )
    if chosen is None:
        raise ValueError("ISS (ZARYA) not found in the latest TLE file.")

    name, line1, line2 = chosen
    satellite = Satrec.twoline2rv(line1, line2)

    now = datetime.now(timezone.utc)
    jd, fr = jday(
        now.year, now.month, now.day,
        now.hour, now.minute,
        now.second + now.microsecond / 1_000_000,
    )

    error, position, velocity = satellite.sgp4(jd, fr)
    print("\n=== SKYTRACE: SGP4 PROPAGATION ===")
    print(f"Object: {name}")
    print(f"NORAD ID: {line1[2:7].strip()}")
    print(f"TLE epoch (UTC): {sat_epoch_datetime(satellite).isoformat()}")
    print(f"Requested time (UTC): {now.isoformat()}")

    if error:
        print(f"SGP4 propagation failed; error code: {error}")
        sys.exit(1)

    x, y, z = position
    vx, vy, vz = velocity
    speed = (vx * vx + vy * vy + vz * vz) ** 0.5
    radius = (x * x + y * y + z * z) ** 0.5

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
    print("This is a propagated estimate from the downloaded TLE, not a live measurement.")


if __name__ == "__main__":
    main()
