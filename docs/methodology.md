# Initial orbital mechanics methodology

## Scope

The first calculation is an idealized circular orbit around Earth. It illustrates the relationship between altitude, orbital speed, and orbital period and establishes a testable scientific-computing baseline.

## Model

The orbital radius is the approximate mean Earth radius plus altitude:

`r = R_E + h`

For a circular two-body orbit, the speed and period are:

`v = sqrt(mu / r)`

`T = 2 pi sqrt(r^3 / mu)`

The implementation uses `R_E = 6371.0 km` and `mu = 398600.4418 km^3/s^2`. Units are kept consistently in kilometres and seconds.

## Assumptions and limitations

- The orbit is circular.
- Earth is treated as a spherical body with a constant gravitational parameter.
- Atmospheric drag, Earth's oblateness, lunar/solar perturbations, and spacecraft manoeuvres are ignored.
- These equations do not propagate real object data and cannot be used by themselves to predict conjunctions or collision probabilities.
- An altitude of zero is mathematically accepted by the function but does not describe a viable orbit above Earth's surface.

## Verification plan

Automated tests check plausibility at a 400 km altitude, monotonic trends (higher circular orbits have lower speed and longer period), and invalid input handling. Further work should compare selected cases with a trusted orbital-mechanics reference and record the exact reference and tolerance used.
