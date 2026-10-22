"""Tests for the ideal circular-orbit calculations."""

import math
import pytest

from skytrace.orbital_mechanics import (
    EARTH_RADIUS_KM,
    circular_orbit,
)


def test_400_km_low_earth_orbit_is_plausible() -> None:
    orbit = circular_orbit(400)
    assert orbit.orbital_radius_km == pytest.approx(EARTH_RADIUS_KM + 400)
    assert orbit.speed_km_s == pytest.approx(7.67, abs=0.03)
    assert orbit.period_minutes == pytest.approx(92.5, abs=0.6)


def test_higher_circular_orbit_is_slower_and_has_longer_period() -> None:
    low = circular_orbit(400)
    high = circular_orbit(2000)
    assert high.speed_km_s < low.speed_km_s
    assert high.period_seconds > low.period_seconds


@pytest.mark.parametrize("altitude", [-1, float("nan"), float("inf"), -float("inf")])
def test_invalid_altitudes_raise_value_error(altitude: float) -> None:
    with pytest.raises(ValueError):
        circular_orbit(altitude)


@pytest.mark.parametrize("altitude", ["400", None, True])
def test_non_numeric_altitudes_raise_type_error(altitude: object) -> None:
    with pytest.raises(TypeError):
        circular_orbit(altitude)  # type: ignore[arg-type]


def test_period_and_speed_are_positive_finite_numbers() -> None:
    orbit = circular_orbit(550)
    assert math.isfinite(orbit.speed_km_s) and orbit.speed_km_s > 0
    assert math.isfinite(orbit.period_seconds) and orbit.period_seconds > 0
