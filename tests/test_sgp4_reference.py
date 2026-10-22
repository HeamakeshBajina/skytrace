from pathlib import Path

import sgp4
from sgp4.api import Satrec


def test_vanguard_epoch_state_matches_sgp4_reference_output():
    """Match the upstream SGP4 verification output for Vanguard 1 at epoch."""
    package_dir = Path(sgp4.__file__).resolve().parent
    tle_path = package_dir / "SGP4-VER.TLE"
    reference_path = package_dir / "tcppver.out"

    if not tle_path.is_file() or not reference_path.is_file():
        import pytest
        pytest.skip("Installed sgp4 verification data is unavailable.")

    tle_lines = tle_path.read_text(encoding="ascii").splitlines()
    tle1 = tle2 = None

    for index, line in enumerate(tle_lines[:-1]):
        if line.startswith("1 00005"):
            tle1 = line
            tle2 = tle_lines[index + 1]
            break

    assert tle1 is not None and tle2 is not None, (
        "Vanguard 1 TLE was not found in SGP4-VER.TLE"
    )

    reference_row = None
    for line in reference_path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if fields and fields[0] == "0.00000000":
            reference_row = fields
            break

    assert reference_row is not None, "Reference epoch row was not found"
    expected = [float(value) for value in reference_row[1:7]]
    assert len(expected) == 6

    satellite = Satrec.twoline2rv(tle1, tle2)
    error, position, velocity = satellite.sgp4(
        satellite.jdsatepoch, satellite.jdsatepochF
    )

    assert error == 0
    actual = list(position) + list(velocity)

    # Upstream verification output is rounded to 8 decimal places for
    # position and 9 for velocity. This tolerance allows for that rounding.
    for actual_value, expected_value in zip(actual, expected):
        assert abs(actual_value - expected_value) < 2e-7