from datetime import datetime, timezone
import math

from sgp4.api import Satrec, jday

# Fixed historical ISS TLE: tests require no downloaded data.
ISS_RECORD = (
    "ISS (ZARYA)",
    "1 25544U 98067A   21275.51005787  .00001490  00000-0  33225-4 0  9993",
    "2 25544  51.6442 208.9163 0003886  121.2047  319.9222 15.48815329302845",
)


def test_fixed_iss_tle_propagates_to_finite_state():
    _, line1, line2 = ISS_RECORD
    satellite = Satrec.twoline2rv(line1, line2)

    # Propagate at the TLE epoch to avoid depending on current time.
    when = datetime(2021, 10, 2, 12, 14, 29, tzinfo=timezone.utc)
    jd, fr = jday(
        when.year, when.month, when.day,
        when.hour, when.minute,
        when.second + when.microsecond / 1_000_000,
    )

    error, position, velocity = satellite.sgp4(jd, fr)

    assert error == 0
    assert all(math.isfinite(value) for value in (*position, *velocity))

    radius = math.sqrt(sum(value * value for value in position))
    speed = math.sqrt(sum(value * value for value in velocity))
    assert 6_000 < radius < 8_000
    assert 6.0 < speed < 9.0
