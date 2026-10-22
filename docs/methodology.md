# SKYTRACE methodology

## Scope

SKYTRACE currently contains two distinct calculation paths:

1. An idealized circular-orbit model for illustrating relationships between altitude, orbital speed, and orbital period.
2. A TLE-based SGP4 workflow for propagating satellite states and screening relative separation.

These paths serve different purposes. The circular-orbit equations are not used as a substitute for SGP4 propagation of the TLE records.

## Idealized circular-orbit model

### Model

The orbital radius is approximated as mean Earth radius plus altitude:

`r = R_E + h`

For a circular two-body orbit, orbital speed and period are:

`v = sqrt(mu / r)`

`T = 2 pi sqrt(r^3 / mu)`

The implementation uses `R_E = 6371.0 km` and `mu = 398600.4418 km^3/s^2`. Units are consistently expressed in kilometres and seconds.

### Assumptions and limitations

- The orbit is circular.
- Earth is treated as a spherical body with a constant gravitational parameter.
- Atmospheric drag, Earth's oblateness, lunar and solar perturbations, and spacecraft manoeuvres are ignored.
- These equations do not propagate real object data and cannot independently predict conjunctions or collision probabilities.
- An altitude of zero is mathematically accepted by the function but does not describe a viable orbit above Earth's surface.

## TLE ingestion and propagation

The data workflow retrieves station Two-Line Element (TLE) records and checks their structure, matching catalog identifiers, and line checksums before saving data. The propagation and screening commands select the latest available station TLE snapshot in `data/raw/`.

For propagation, each TLE pair is parsed into an SGP4 satellite record. The propagated state contains position and velocity in the TEME reference frame, with position in kilometres and velocity in kilometres per second. Propagation errors and non-finite state values are rejected rather than treated as valid results.

TLE epoch age is reported as a data-freshness indicator. Age is not an estimate of orbital uncertainty and does not, by itself, establish the accuracy of a propagated state.

## Close-approach screening

### Instantaneous mode

Instantaneous screening propagates the available records to one timezone-aware timestamp and computes pairwise Euclidean separation between propagated position vectors:

`d = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)`

The separation is expressed in kilometres. Pairs with numerically duplicate propagated states are flagged as data-quality findings and excluded from the ordinary closest-pair ranking.

### Sampled-window mode

Sampled-window screening evaluates pairs at discrete timestamps from the requested start through the end of the interval. The end timestamp is included even when the interval length is not an exact multiple of the requested sampling step.

For each successfully evaluated pair, the reported separation is the smallest separation among the timestamps actually sampled. The method records the time of that sampled minimum and the number of samples evaluated.

**A sampled minimum is not guaranteed to be the continuous-time minimum.** A close approach occurring between sample timestamps may be missed or have a smaller actual separation than the reported value. Results depend on the selected time interval, sampling step, and input TLE quality.

Pairs with numerically matching states across the sampled window are flagged as data-quality findings, not as collision alerts. Propagation failures are reported rather than silently represented as successful results.

## JSON screening contract

The command-line screening tool supports text output and a machine-readable JSON format selected with `--format json`. JSON documents include a schema version, generation timestamp, input data file, screening settings, TLE freshness records, units, screening results, data-quality flags, a summary, and limitations.

Screening result records identify objects by name and catalog identifier. Consumers should validate the schema version and treat the output as preliminary geometric screening, not as a collision probability or an operational risk classification.

## Verification

The automated test suite covers scientific calculations, input validation, propagation and screening command-line behavior, and the JSON output contract. Tests using fixed TLE fixtures provide reproducible checks of CLI behavior. Successful tests establish that the tested implementation meets those test expectations; they do not independently validate orbital predictions against operational conjunction data.

Further scientific validation should compare selected propagated cases against a trusted independent reference, documenting the reference, epoch, coordinate frame, units, and acceptable tolerances.

## Overall limitations

- TLE data quality and age affect the interpretation of propagated states.
- The current sampled-window method does not guarantee a continuous-time minimum.
- Duplicate-state flags are data-quality diagnostics.
- No collision probability, covariance-based uncertainty propagation, or operational risk assessment is performed.
- Results should not be used as the sole basis for spacecraft manoeuvres or collision-avoidance decisions.
