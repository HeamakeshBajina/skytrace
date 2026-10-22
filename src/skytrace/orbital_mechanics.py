"""Simple, idealized orbital mechanics calculations.

These calculations assume a circular orbit in a two-body Earth-satellite model.
They do not account for atmospheric drag, Earth's oblateness, third-body effects,
or manoeuvres, and are not suitable for operational conjunction assessment.
"""

from dataclasses import dataclass
import math

# Standard approximate values; distances are in km and time in seconds.
EARTH_RADIUS_KM = 6371.0
EARTH_MU_KM3_S2 = 398600.4418
SECONDS_PER_MINUTE = 60.0
SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class CircularOrbit:
    """Derived values for an ideal circular Earth orbit."""

    altitude_km: float
    orbital_radius_km: float
    speed_km_s: float
    period_seconds: float

    @property
    def period_minutes(self) -> float:
        """Orbital period in minutes."""
        return self.period_seconds / SECONDS_PER_MINUTE

    @property
    def period_hours(self) -> float:
        """Orbital period in hours."""
        return self.period_seconds / SECONDS_PER_HOUR


def circular_orbit(altitude_km: float) -> CircularOrbit:
    """Calculate speed and period for an ideal circular orbit at an altitude.

    Args:
        altitude_km: Altitude above the approximate mean Earth radius, in km.

    Returns:
        A :class:`CircularOrbit` with orbital radius, circular speed, and period.

    Raises:
        TypeError: If altitude_km is not a real numeric value.
        ValueError: If altitude_km is negative or not finite.

    Note:
        An altitude of zero is mathematically accepted but is not a physically
        realistic orbit above Earth's surface. Results are educational estimates.
    """
    if isinstance(altitude_km, bool) or not isinstance(altitude_km, (int, float)):
        raise TypeError("altitude_km must be a real number")
    if not math.isfinite(altitude_km) or altitude_km < 0:
        raise ValueError("altitude_km must be finite and non-negative")

    radius_km = EARTH_RADIUS_KM + float(altitude_km)
    speed_km_s = math.sqrt(EARTH_MU_KM3_S2 / radius_km)
    period_seconds = 2.0 * math.pi * math.sqrt(radius_km**3 / EARTH_MU_KM3_S2)

    return CircularOrbit(
        altitude_km=float(altitude_km),
        orbital_radius_km=radius_km,
        speed_km_s=speed_km_s,
        period_seconds=period_seconds,
    )
