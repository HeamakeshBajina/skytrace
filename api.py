import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from skytrace.epoch_age import add_epoch_age_summary

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "screen_approaches.py"
FETCH_SCRIPT = ROOT / "scripts" / "fetch_satellites.py"
OMM_SCRIPT = ROOT / "scripts" / "screen_omm.py"
def configured_max_tle_age_hours():
    raw_value = os.environ.get("SKYTRACE_MAX_TLE_AGE_HOURS", "6")
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "SKYTRACE_MAX_TLE_AGE_HOURS must be a number between 0.1 and 72."
        ) from exc
    if not 0.1 <= value <= 72:
        raise RuntimeError(
            "SKYTRACE_MAX_TLE_AGE_HOURS must be between 0.1 and 72 hours."
        )
    return value


MAX_TLE_AGE_HOURS = configured_max_tle_age_hours()
REFRESH_FAILURE_COOLDOWN_SECONDS = 3600
_last_refresh_failure_at = None
_last_refresh_failure_detail = None

app = FastAPI(title="SKYTRACE Screening API", version="1.1.0")



def snapshot_candidates():
    raw = ROOT / "data" / "raw"
    omm = sorted(
        raw.glob("stations_*.omm.xml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    tle = sorted(
        raw.glob("stations_*.tle"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return omm + tle


def latest_snapshot():
    candidates = snapshot_candidates()
    return candidates[0] if candidates else None


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


def load_snapshot_records(tle_path):
    try:
        lines = [
            line.strip()
            for line in tle_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
    except OSError as exc:
        raise HTTPException(status_code=503, detail="TLE snapshot could not be read.") from exc

    if not lines or len(lines) % 3:
        raise HTTPException(status_code=503, detail="TLE snapshot does not contain complete records.")

    records = []
    for index in range(0, len(lines), 3):
        name, line1, line2 = lines[index:index + 3]
        if not line1.startswith("1 ") or not line2.startswith("2 ") or line1[2:7] != line2[2:7]:
            raise HTTPException(status_code=503, detail="TLE snapshot contains an invalid record.")
        records.append((name, line1, line2))
    return records



def assess_snapshot(snapshot_path, reference_time=None):
    reference_time = reference_time or datetime.now(timezone.utc)

    if snapshot_path.name.endswith(".omm.xml"):
        from scripts.fetch_satellites import parse_omm_xml
        from skytrace.time_window import filter_fresh_omm_records

        try:
            text = snapshot_path.read_text(encoding="utf-8-sig")
            records = parse_omm_xml(text)
        except (OSError, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="OMM snapshot could not be parsed.",
            ) from exc

        eligible, report = filter_fresh_omm_records(
            records, reference_time, MAX_TLE_AGE_HOURS
        )
    else:
        from skytrace.time_window import filter_fresh_tle_records
        records = load_snapshot_records(snapshot_path)
        eligible, report = filter_fresh_tle_records(
            records, reference_time, MAX_TLE_AGE_HOURS
        )

    counts = {
        "fresh": 0,
        "stale": 0,
        "future_epoch": 0,
        "invalid_epoch": 0,
    }
    for item in report:
        status = item.get("status")
        counts[status] = counts.get(status, 0) + 1

    return records, eligible, report, counts



def ensure_fresh_snapshot():
    global _last_refresh_failure_at, _last_refresh_failure_detail

    def find_usable_snapshot():
        last_detail = None
        for candidate in snapshot_candidates():
            try:
                _, eligible, _, counts = assess_snapshot(candidate)
                if len(eligible) >= 2:
                    return candidate, None
                candidate_detail = (
                    f"{candidate.name}: fewer than two fresh records "
                    f"(fresh={counts['fresh']}, stale={counts['stale']}, "
                    f"future_epoch={counts['future_epoch']}, "
                    f"invalid_epoch={counts['invalid_epoch']})."
                )
                if last_detail is None:
                    last_detail = candidate_detail
            except HTTPException as exc:
                last_detail = str(exc.detail)

        return None, last_detail

    current, detail = find_usable_snapshot()
    if current is not None:
        _last_refresh_failure_at = None
        _last_refresh_failure_detail = None
        return current

    if _last_refresh_failure_at is not None:
        elapsed = time.monotonic() - _last_refresh_failure_at
        remaining = REFRESH_FAILURE_COOLDOWN_SECONDS - elapsed
        if remaining > 0:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No usable fresh orbital snapshot is available. "
                    f"Refresh retry in about {int(remaining) + 1} seconds. "
                    f"{_last_refresh_failure_detail or detail or ''}"
                ),
            )

    if not FETCH_SCRIPT.is_file():
        raise HTTPException(
            status_code=500,
            detail="Satellite data refresh script is missing.",
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
        _last_refresh_failure_detail = "Satellite data refresh timed out."
        raise HTTPException(
            status_code=503,
            detail=_last_refresh_failure_detail,
        ) from exc

    # Forward bounded fetcher output to Render logs for provider diagnosis.
    # The fetcher does not print credentials; this patch does not read or log env vars.
    refresh_stdout = (refresh.stdout or "").strip()
    refresh_stderr = (refresh.stderr or "").strip()

    if refresh_stdout:
        print(
            "[SKYTRACE DATA REFRESH] stdout:\n" + refresh_stdout[-4000:],
            flush=True,
        )
    if refresh_stderr:
        print(
            "[SKYTRACE DATA REFRESH] stderr:\n" + refresh_stderr[-4000:],
            flush=True,
        )
    if not refresh_stdout and not refresh_stderr:
        print(
            "[SKYTRACE DATA REFRESH] Fetcher completed without console output.",
            flush=True,
        )

    if refresh.returncode != 0:
        _last_refresh_failure_at = time.monotonic()
        _last_refresh_failure_detail = (
            refresh.stderr.strip()[-1000:]
            or "Satellite data source unavailable."
        )
        raise HTTPException(
            status_code=503,
            detail="Satellite data refresh failed. "
                   + _last_refresh_failure_detail,
        )

    current, detail = find_usable_snapshot()
    if current is None:
        _last_refresh_failure_at = time.monotonic()
        _last_refresh_failure_detail = (
            "Refresh completed, but no snapshot contains at least "
            "two fresh records. " + (detail or "")
        )
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
    """Return current SGP4 state vectors from the freshest available format."""
    snapshot = ensure_fresh_snapshot()
    propagated_at = datetime.now(timezone.utc)

    records, eligible, freshness_report, freshness_counts = assess_snapshot(
        snapshot, propagated_at
    )

    if len(eligible) < 2:
        raise HTTPException(
            status_code=503,
            detail="Fewer than two fresh orbital records are available.",
        )

    is_omm = snapshot.name.endswith(".omm.xml")

    try:
        if is_omm:
            from scripts.screen_approaches import propagate_omm_records
            states = propagate_omm_records(eligible, propagated_at)
            element_format = "OMM-XML"
            engine = "python-sgp4-omm"
        else:
            from scripts.screen_approaches import propagate_records
            states = propagate_records(eligible, propagated_at)
            element_format = "TLE"
            engine = "python-sgp4-tle"

        if len(states) < 2:
            raise HTTPException(
                status_code=503,
                detail="Fewer than two orbital objects propagated successfully.",
            )

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
            "element_format": element_format,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "propagated_at_utc": propagated_at.isoformat(),
            "data_file": snapshot.name,
            "source": metadata.get(
                "source", "Unknown; source metadata unavailable"
            ),
            "snapshot_age_hours": age_hours,
            "retrieval_age_hours": age_hours,
            "tle_freshness": {
                "max_age_hours": MAX_TLE_AGE_HOURS,
                "eligible_count": len(eligible),
                "excluded_count": len(records) - len(eligible),
                "counts": freshness_counts,
                "records": freshness_report,
            },
            "coordinate_frame": "TEME",
            "units": {
                "position": "km",
                "velocity": "km/s",
                "time": "ISO-8601 UTC",
            },
            "limitations": [
                "Positions are SGP4 states in the TEME reference frame.",
                "TEME coordinates are not Earth-fixed geographic coordinates.",
                "Element age alone does not quantify orbital uncertainty.",
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
                "X-SKYTRACE-Engine": engine,
            },
        )

    except HTTPException:
        raise
    except (OSError, ValueError, ImportError, RuntimeError, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Orbital visualization data could not be generated: {exc}",
        ) from exc



@app.get("/api/screening")
def screening(
    top: int = Query(default=50, ge=1, le=200),
    hours: int = Query(default=0, ge=0, le=24),
    step_seconds: int = Query(default=60, ge=10, le=600),
):
    snapshot = ensure_fresh_snapshot()
    is_omm = snapshot.name.endswith(".omm.xml")

    selected_script = (
        ROOT / "scripts" / "screen_omm.py"
        if is_omm else SCRIPT
    )

    if not selected_script.is_file():
        raise HTTPException(
            status_code=500,
            detail="Selected orbital screening engine is missing.",
        )

    command = [sys.executable, str(selected_script)]

    if is_omm:
        command.extend([
            "--data-file", str(snapshot),
            "--hours", str(hours),
            "--step-seconds", str(step_seconds),
            "--top", str(top),
            "--max-age-hours", str(MAX_TLE_AGE_HOURS),
        ])
    else:
        command.extend([
            "--hours", str(hours),
            "--step-seconds", str(step_seconds),
            "--top", str(top),
            "--format", "json",
        ])

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            raw_detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Screening engine failed."
            )

            if (
                is_omm
                and "OMM screening stopped: fewer than two fresh records."
                in raw_detail
            ):
                freshness_counts = {}
                json_start = raw_detail.rfind("{")
                json_end = raw_detail.rfind("}")

                if json_start >= 0 and json_end > json_start:
                    try:
                        freshness_counts = json.loads(
                            raw_detail[json_start:json_end + 1]
                        )
                    except (ValueError, TypeError):
                        freshness_counts = {}

                detail = {
                    "code": "insufficient_fresh_omm_records",
                    "message": (
                        "OMM screening requires at least two fresh orbital "
                        "records. Screening was safely not performed."
                    ),
                    "snapshot": snapshot.name,
                    "max_age_hours": MAX_TLE_AGE_HOURS,
                    "freshness": freshness_counts,
                }
            else:
                detail = {
                    "code": "screening_engine_failed",
                    "message": (
                        "The screening engine failed. Check backend logs "
                        "for diagnostic details."
                    ),
                }

            raise HTTPException(status_code=503, detail=detail)

        payload = json.loads(result.stdout)
        payload = add_epoch_age_summary(payload)
        payload["element_format"] = "OMM-XML" if is_omm else "TLE"

        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "X-SKYTRACE-Engine": (
                    "python-sgp4-omm" if is_omm else "python-sgp4-tle"
                ),
            },
        )

    except HTTPException:
        raise
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="Screening timed out.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Screening engine returned invalid JSON.",
        ) from exc
