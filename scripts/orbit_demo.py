from skytrace.orbital_mechanics import circular_orbit


def main() -> None:
    altitude_km = 400.0
    orbit = circular_orbit(altitude_km)

    print("\n=== SKYTRACE ORBIT ANALYSIS ===")
    print(f"Altitude:       {orbit.altitude_km:.1f} km")
    print(f"Radius:         {orbit.orbital_radius_km:.2f} km")
    print(f"Orbital speed:  {orbit.speed_km_s:.4f} km/s")
    print(f"Period:         {orbit.period_minutes:.2f} minutes")
    print(f"Period:         {orbit.period_hours:.4f} hours")

    assert abs(orbit.speed_km_s - 7.67) < 0.02
    assert abs(orbit.period_minutes - 92.5) < 0.5

    print("\nVALIDATION PASSED")


if __name__ == "__main__":
    main()
