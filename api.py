import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "screen_approaches.py"
FETCH_SCRIPT = ROOT / "scripts" / "fetch_satellites.py"
MAX_TLE_AGE_HOURS = 6
REFRESH_FAILURE_COOLDOWN_SECONDS = 3600
_last_refresh_failure_at = None
_last_refresh_failure_detail = None

app = FastAPI(title="SKYTRACE Screening API", version="1.1.0")


def latest_snapshot():
    files = sorted(
        (ROOT / "data" / "raw").glob("stations_*.tle"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def snapshot_age_hours(tle_path):
    # Retrieval metadata is required: a recent Git checkout timestamp
    # must not make an old committed snapshot appear fresh.
    metadata_path = tle_path.with_suffix(".json")
    if not metadata_path.is_file():
        return None

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        retrieved = datetime.fromisoformat(
            metadata["retrieved_at_utc"].replace("Z", "+00:00")
        )
        if retrieved.tzinfo is None or retrieved.utcoffset() is None:
            return None
        age = (
            datetime.now(timezone.utc) - retrieved.astimezone(timezone.utc)
        ).total_seconds() / 3600
        return age
    except (OSError, ValueError, KeyError, TypeError):
        return None


def ensure_fresh_snapshot():
    global _last_refresh_failure_at, _last_refresh_failure_detail

    current = latest_snapshot()
    age = snapshot_age_hours(current) if current else None

    # A verifiably fresh snapshot can be used without contacting the source.
    if current is not None and age is not None and 0 <= age <= MAX_TLE_AGE_HOURS:
        return current

    # Avoid repeated upstream requests after a recent failed refresh.
    if _last_refresh_failure_at is not None:
        elapsed = time.monotonic() - _last_refresh_failure_at
        remaining = REFRESH_FAILURE_COOLDOWN_SECONDS - elapsed
        if remaining > 0:
            raise HTTPException(
                status_code=503,
                detail=(
                    "TLE refresh recently failed; retry in about "
                    f"{int(remaining) + 1} seconds. Screening was not run."
                ),
            )

    try:
        refresh = subprocess.run(
            [sys.executable, str(FETCH_SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=100,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _last_refresh_failure_at = time.monotonic()
        _last_refresh_failure_detail = "TLE refresh timed out."
        raise HTTPException(
            status_code=503,
            detail="TLE refresh timed out; screening was not run.",
        ) from exc

    if refresh.returncode != 0:
        _last_refresh_failure_at = time.monotonic()
        _last_refresh_failure_detail = (
            refresh.stderr.strip()[-500:]
            or "Satellite data source unavailable."
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "TLE refresh failed; screening was not run. "
                + _last_refresh_failure_detail
            ),
        )

    current = latest_snapshot()
    age = snapshot_age_hours(current) if current else None

    if current is None or age is None or age < 0 or age > MAX_TLE_AGE_HOURS:
        _last_refresh_failure_at = time.monotonic()
        _last_refresh_failure_detail = "No verifiably fresh TLE snapshot is available."
        raise HTTPException(
            status_code=503,
            detail=_last_refresh_failure_detail,
        )

    _last_refresh_failure_at = None
    _last_refresh_failure_detail = None
    return current


@app.get("/health")
def health():
    return {"service": "SKYTRACE", "status": "ok"}



@app.get("/api/orbits")
def orbits():
    """Return current SGP4 state vectors for the orbital visualization."""
    if not FETCH_SCRIPT.is_file():
        raise HTTPException(
            status_code=500,
            detail="TLE refresh script is missing.",
        )

    snapshot = ensure_fresh_snapshot()
    if snapshot is None or not snapshot.is_file():
        raise HTTPException(
            status_code=503,
            detail="No usable TLE snapshot is available.",
        )

    try:
        # Import the existing propagator; do not create a second orbital model.
        from scripts.screen_approaches import propagate_records

        lines = [
            line.strip()
            for line in snapshot.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if not lines or len(lines) % 3:
            raise HTTPException(
                status_code=503,
                detail="TLE snapshot does not contain complete records.",
            )

        records = []
        for index in range(0, len(lines), 3):
            name, line1, line2 = lines[index:index + 3]
            if (
                not line1.startswith("1 ")
                or not line2.startswith("2 ")
                or line1[2:7] != line2[2:7]
            ):
                raise HTTPException(
                    status_code=503,
                    detail="TLE snapshot contains an invalid record.",
                )
            records.append((name, line1, line2))

        propagated_at = datetime.now(timezone.utc)
        states = propagate_records(records, propagated_at)

        metadata_path = snapshot.with_suffix(".json")
        metadata = {}
        if metadata_path.is_file():
            try:
                metadata = json.loads(
                    metadata_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                metadata = {}

        age_hours = snapshot_age_hours(snapshot)

        payload = {
            "schema_version": "1.0",
            "product": "SKYTRACE",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "propagated_at_utc": propagated_at.isoformat(),
            "data_file": snapshot.name,
            "source": metadata.get("source", "Unknown; source metadata unavailable"),
            "snapshot_age_hours": age_hours,
            "coordinate_frame": "TEME",
            "units": {
                "position": "km",
                "velocity": "km/s",
                "time": "ISO-8601 UTC",
            },
            "limitations": [
                "Positions are SGP4 states in the TEME reference frame.",
                "TEME coordinates are not Earth-fixed geographic coordinates.",
                "TLE age alone does not quantify orbital uncertainty.",
                "This endpoint does not estimate collision probability.",
            ],
            "object_count": len(states),
            "objects": [
                {
                    "name": state["name"],
                    "catalog_id": state["catalog_id"],
                    "position_km": list(state["position"]),
                    "velocity_km_s": list(state["velocity"]),
                }
                for state in states
            ],
        }

        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "X-SKYTRACE-Engine": "python-sgp4",
            },
        )

    except HTTPException:
        raise
    except (OSError, ValueError, ImportError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Orbital visualization data could not be generated.",
        ) from exc


@app.get("/api/screening")
def screening(top: int = Query(default=50, ge=1, le=200)):
    if not SCRIPT.is_file() or not FETCH_SCRIPT.is_file():
        raise HTTPException(
            status_code=500,
            detail="Screening or TLE refresh script is missing.",
        )

    ensure_fresh_snapshot()

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--hours", "0",
                "--top", str(top),
                "--format", "json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            detail = result.stderr.strip()[-2000:] or "Screening engine failed."
            raise HTTPException(status_code=503, detail=detail)

        payload = json.loads(result.stdout)
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "X-SKYTRACE-Engine": "python-sgp4",
            },
        )

    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Screening timed out.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Screening engine returned invalid JSON.",
        ) from exc
