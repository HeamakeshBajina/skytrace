import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.fetch_satellites import valid_tle_line


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "screen_approaches.py"
FIXED_START = "2026-10-22T12:00:00Z"

ISS_LINE1 = (
    "1 25544U 98067A   26294.04791053  .00009575  00000+0  18188-3 0  9996"
)
ISS_LINE2 = (
    "2 25544  51.6327  37.2623 0006759 289.5321  70.4938 15.48967427591263"
)


def with_valid_checksum(line):
    """Return a 69-character TLE line with a recalculated checksum."""
    if len(line) != 69:
        raise ValueError(f"Expected 69-character TLE line, got {len(line)}")
    checksum = sum(
        int(c) if c.isdigit() else 1 if c == "-" else 0
        for c in line[:68]
    ) % 10
    return line[:68] + str(checksum)


def make_test_tle_text():
    """Create two distinct TLE records with valid checksums."""
    second_line1 = with_valid_checksum(
        ISS_LINE1[:2] + "25545" + ISS_LINE1[7:]
    )

    # The mean-anomaly field is exactly nine characters: positions 43:52.
    second_line2_base = (
        ISS_LINE2[:2] + "25545" + ISS_LINE2[7:]
    )
    second_line2 = with_valid_checksum(
        second_line2_base[:43] + "100.0000 " + second_line2_base[52:]
    )

    records = [
        ("TEST OBJECT A", ISS_LINE1, ISS_LINE2),
        ("TEST OBJECT B", second_line1, second_line2),
    ]

    for name, line1, line2 in records:
        assert len(line1) == 69, f"Bad line 1 length for {name}: {len(line1)}"
        assert len(line2) == 69, f"Bad line 2 length for {name}: {len(line2)}"
        assert valid_tle_line(line1, 1), f"Bad line 1 checksum for {name}"
        assert valid_tle_line(line2, 2), f"Bad line 2 checksum for {name}"
        assert line1[2:7] == line2[2:7], f"Catalog mismatch for {name}"

    return "".join(f"{name}\n{line1}\n{line2}\n" for name, line1, line2 in records)


def run_cli(*arguments, cwd=PROJECT_ROOT):
    environment = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def create_tle_dataset(directory):
    raw = directory / "data" / "raw"
    raw.mkdir(parents=True)
    target = raw / "stations_test_fixture.tle"
    target.write_text(make_test_tle_text(), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    ("arguments", "expected_message"),
    [
        (("--hours", "-1"), "--hours must be finite and non-negative."),
        (("--hours", "nan"), "--hours must be finite and non-negative."),
        (("--hours", "inf"), "--hours must be finite and non-negative."),
        (("--step-seconds", "0"), "--step-seconds must be finite and positive."),
        (("--step-seconds", "-5"), "--step-seconds must be finite and positive."),
        (("--step-seconds", "nan"), "--step-seconds must be finite and positive."),
        (("--top", "0"), "--top must be at least 1."),
        (("--start", "2026-10-22T12:00:00"), "Timestamp must include Z or a UTC offset."),
    ],
)
def test_invalid_cli_arguments_exit_with_usage_error(arguments, expected_message):
    result = run_cli(*arguments)
    assert result.returncode == 2
    assert expected_message in result.stderr


def test_help_exits_successfully():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--hours" in result.stdout
    assert "--step-seconds" in result.stdout
    assert "--start" in result.stdout
    assert "--top" in result.stdout


def test_fixture_tle_lines_have_valid_checksums_and_matching_catalog_ids():
    lines = [line for line in make_test_tle_text().splitlines() if line]
    assert len(lines) == 6

    for index in (1, 4):
        assert len(lines[index]) == 69
        assert len(lines[index + 1]) == 69
        assert valid_tle_line(lines[index], 1)
        assert valid_tle_line(lines[index + 1], 2)
        assert lines[index][2:7] == lines[index + 1][2:7]

    assert lines[1][2:7] != lines[4][2:7]
    assert "70.4938" in lines[2]
    assert "100.0000" in lines[5]


def test_instantaneous_screening_cli_succeeds_with_fixture(tmp_path):
    create_tle_dataset(tmp_path)
    result = run_cli("--start", FIXED_START, "--top", "3", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Mode: instantaneous" in result.stdout
    assert "Input objects: 2" in result.stdout
    assert "Objects propagated: 2" in result.stdout
    assert "Pairs evaluated: 1" in result.stdout
    assert "CLOSEST NON-DUPLICATE PAIRS" in result.stdout
    assert "No collision probability or operational risk assessment" in result.stdout


def test_sampled_window_screening_cli_succeeds_with_fixture(tmp_path):
    create_tle_dataset(tmp_path)
    result = run_cli(
        "--start", FIXED_START,
        "--hours", "0.05",
        "--step-seconds", "60",
        "--top", "3",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Mode: sampled time window" in result.stdout
    assert "End time (UTC):" in result.stdout
    assert "Non-duplicate pairs successfully screened:" in result.stdout
    assert "Pairs skipped due to errors:" in result.stdout
    assert "CLOSEST NON-DUPLICATE PAIRS" in result.stdout
    assert "No collision probability or operational risk assessment" in result.stdout

def test_json_instantaneous_screening_cli(tmp_path):
    import json

    create_tle_dataset(tmp_path)
    result = run_cli(
        "--start", FIXED_START, "--format", "json", cwd=tmp_path
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["screening"]["mode"] == "instantaneous"
    assert payload["units"]["separation"] == "km"
    assert payload["summary"]["objects_propagated"] == 2
    assert len(payload["results"]) == 1
    assert payload["results"][0]["separation_km"] >= 0
    assert payload["results"][0]["catalog_id_a"]
    assert payload["results"][0]["catalog_id_b"]
    assert "No collision probability" in " ".join(payload["limitations"])


def test_json_sampled_window_screening_cli(tmp_path):
    import json

    create_tle_dataset(tmp_path)
    result = run_cli(
        "--start", FIXED_START,
        "--hours", "0.05",
        "--step-seconds", "60",
        "--format", "json",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["screening"]["mode"] == "sampled_window"
    assert payload["screening"]["end_utc"]
    assert payload["summary"]["pairs_screened_successfully"] == 1
    assert payload["results"][0]["time_utc"]
    assert payload["results"][0]["catalog_id_a"]
    assert payload["results"][0]["catalog_id_b"]
    assert payload["results"][0]["samples_evaluated"] >= 2
    assert "continuous-time minima" in " ".join(payload["limitations"])


def test_text_format_remains_the_default(tmp_path):
    create_tle_dataset(tmp_path)
    result = run_cli("--start", FIXED_START, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Mode: instantaneous" in result.stdout
    assert not result.stdout.lstrip().startswith("{")


def test_json_instantaneous_duplicate_names_are_distinguished_by_catalog_id(tmp_path):
    import json

    fixture = create_tle_dataset(tmp_path)
    lines = fixture.read_text(encoding="utf-8").splitlines()
    lines[0] = "REUSED NAME"
    lines[3] = "REUSED NAME"
    fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = run_cli("--start", FIXED_START, "--format", "json", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["summary"]["duplicate_state_pairs"] == 0
    assert payload["summary"]["pairs_screened"] == 1
    assert len(payload["results"]) == 1
    assert {payload["results"][0]["catalog_id_a"], payload["results"][0]["catalog_id_b"]} == {
        "25544", "25545"
    }


def test_json_sampled_window_duplicate_names_are_distinguished_by_catalog_id(tmp_path):
    import json

    fixture = create_tle_dataset(tmp_path)
    lines = fixture.read_text(encoding="utf-8").splitlines()
    lines[0] = "REUSED NAME"
    lines[3] = "REUSED NAME"
    fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = run_cli(
        "--start", FIXED_START,
        "--hours", "0.05",
        "--step-seconds", "60",
        "--format", "json",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["summary"]["duplicate_state_pairs"] == 0
    assert payload["summary"]["pairs_screened_successfully"] == 1
    assert len(payload["results"]) == 1
    assert {payload["results"][0]["catalog_id_a"], payload["results"][0]["catalog_id_b"]} == {
        "25544", "25545"
    }