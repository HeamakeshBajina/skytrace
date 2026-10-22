import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "propagate_satellite.py"


def run_cli(*arguments, cwd=PROJECT_ROOT):
    env = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )


def test_help_displays_usage_without_propagating():
    result = run_cli("--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "usage:" in result.stdout.lower()
    assert "--time" in result.stdout
    assert "TEME position" not in result.stdout


def test_naive_timestamp_is_rejected():
    result = run_cli("--time", "2026-10-22T12:00:00")
    assert result.returncode == 2
    assert "Timestamp must include Z or a UTC offset." in result.stderr


def test_invalid_timestamp_is_rejected():
    result = run_cli("--time", "not-a-timestamp")
    assert result.returncode == 2
    assert "Use ISO-8601" in result.stderr


def test_fixed_time_propagation_succeeds():
    result = run_cli("--time", "2026-10-22T12:00:00Z")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TEME position (km)" in result.stdout
    assert "Requested time (UTC): 2026-10-22T12:00:00+00:00" in result.stdout
    assert "not a live measurement" in result.stdout