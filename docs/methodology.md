# SKYTRACE — Methodology

## 1. Scope and distinct calculation paths

SKYTRACE contains separate models and data-processing paths:

1. An idealized circular-orbit model illustrating the relationship between altitude, orbital speed, and orbital period.
2. A TLE ingestion and SGP4 propagation path.
3. An OMM XML ingestion and SGP4 propagation path.
4. Instantaneous and sampled-window geometric separation screening.

The circular-orbit equations are not used as a substitute for SGP4 propagation of GP element records.

## 2. Idealized circular-orbit model

The orbital radius is approximated as mean Earth radius plus altitude:

`r = R_E + h`

For a circular two-body orbit:

`v = sqrt(mu / r)`

`T = 2 pi sqrt(r^3 / mu)`

The implementation uses `R_E = 6371.0 km` and `mu = 398600.4418 km^3/s^2`. Units are kilometres and seconds.

Assumptions and limitations:

- The orbit is circular.
- Earth is treated as spherical with a constant gravitational parameter.
- Atmospheric drag, Earth's oblateness, lunar and solar perturbations, and spacecraft manoeuvres are ignored.
- These equations do not propagate real object data and cannot independently predict conjunctions or collision probabilities.
- An altitude of zero is mathematically accepted by the function but does not describe a viable orbit above Earth's surface.

## 3. GP element ingestion

### 3.1 TLE path

The TLE fetcher retrieves station-group GP data and validates record structure, matching catalog identifiers, and line checksums before saving the data and metadata. TLE records are parsed into SGP4 satellite objects. The TLE catalog field supports only five-digit identifiers.

### 3.2 OMM XML path

The OMM fetcher retrieves station-group GP data in XML form, parses OMM records, and initializes SGP4 satellite objects using `python-sgp4`. Snapshot metadata records the source URL, retrieval timestamp, record count, format, and validation description.

OMM is a standardized message representation for orbital mean elements and associated metadata. It can represent catalog identifiers beyond the five-digit TLE limitation. OMM XML is not inherently more accurate than TLE: the underlying element source, epoch, and fit quality remain important.

### 3.3 Snapshot discovery and fallback

The API's snapshot discovery prefers OMM snapshots and retains a TLE fallback path. Each candidate is assessed against the configured freshness rule. A recently retrieved file is not assumed to contain recent elements: retrieval timestamp and element epoch are distinct.

The fetcher can use Space-Track when the required credentials are configured; otherwise its implemented fallback path uses CelesTrak. Data provenance is retained in snapshot metadata.

## 4. Epoch interpretation and freshness

Freshness is computed from each record's element epoch relative to a timezone-aware reference time.

- TLE epochs are parsed from the TLE epoch field.
- OMM epochs are parsed from the OMM `EPOCH` field.
- Explicit timezone offsets are normalized to UTC.
- A naive OMM epoch is interpreted as UTC only when `TIME_SYSTEM=UTC`.
- A naive OMM epoch without that supported UTC declaration is invalid.
- Future epochs and invalid epochs are not treated as fresh.

The default maximum age is six hours. The configurable range is 0.1–72 hours. The API/TLE path reads `SKYTRACE_MAX_TLE_AGE_HOURS`; the OMM screening CLI accepts `--max-age-hours`. A threshold is an inclusion policy, not a model of orbital uncertainty and not a claim that an element set is accurate up to that age.

Where fewer than two eligible records are available, screening stops. The API may return HTTP 503 with a structured insufficient-fresh-data detail. This is deliberate safety behavior, distinct from backend process health.

## 5. SGP4 propagation and state representation

TLE and OMM GP records are initialized for SGP4 propagation. The current implementation reports position in kilometres and velocity in kilometres per second in the TEME reference frame. Propagation errors and non-finite state values must not be treated as valid states.

The fact that two input formats initialize the same propagation model does not imply that their source elements are identical or equally current.

## 6. Close-approach screening

### 6.1 Instantaneous mode

Instantaneous screening propagates eligible records to one timezone-aware timestamp and computes pairwise Euclidean separation:

`d = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)`

The result is expressed in kilometres. Numerically duplicate propagated states are flagged as data-quality findings and excluded from ordinary closest-pair ranking.

The dashboard's current screening action is instantaneous.

### 6.2 Sampled-window mode

The TLE screening CLI supports sampled-window operation through `scripts/screen_approaches.py`. The OMM sampled-window CLI is `scripts/screen_omm.py`; it accepts a required OMM XML `--data-file`, plus `--hours`, `--step-seconds`, `--top`, `--max-age-hours`, and optional `--start` arguments.

Sampled-window screening evaluates pairs at discrete timestamps across the requested interval. The end timestamp is included even when the interval length is not an exact multiple of the requested sampling step. For each evaluated pair, the reported separation is the smallest separation among timestamps actually sampled.

**A sampled minimum is not guaranteed to be the continuous-time minimum.** A closer approach between sample timestamps may be missed. Results depend on the selected interval, sampling step, and input element quality. Propagation failures are reported rather than silently represented as successful results.

## 7. JSON screening contract

The TLE screening CLI supports text output and machine-readable JSON selected with `--format json`. Its versioned JSON document includes generation metadata, input file, screening settings, timestamps, freshness information, units, results, data-quality flags, a summary, and limitations.

Consumers should validate the schema version and treat output as preliminary geometric screening, not as collision probability or operational risk classification. Do not assume the OMM CLI has the identical JSON schema unless verified from its current output.

## 8. API behavior

The FastAPI service exposes:

- `GET /health` — process health.
- `GET /api/orbits` — orbital data for the dashboard, subject to snapshot discovery and freshness checks.
- `GET /api/screening` — dashboard screening response, currently instantaneous and subject to the same input-data safety checks.

A healthy `/health` response does not prove fresh orbital data is available. HTTP 503 can indicate that no candidate snapshot contains at least two fresh records, or that a refresh retry cooldown is active. Error details should identify the data condition without exposing internal tracebacks.

## 9. Verification

The automated test suite covers scientific calculations, input validation, propagation and screening CLI behavior, freshness handling, and related API/data paths. Fixed fixtures provide reproducible software checks.

Passing tests establish that the tested implementation meets those test expectations; they do not independently validate orbital predictions against operational conjunction data. Further scientific validation should compare selected propagated cases against a trusted independent reference and document the reference, epoch, coordinate frame, units, and tolerances.

## 10. Overall limitations

- GP element age and provenance affect interpretation; age alone does not quantify orbital uncertainty.
- Sampled-window minima are discrete sampled minima, not guaranteed continuous-time minima.
- No collision probability, covariance-based uncertainty propagation, or operational risk assessment is performed.
- Duplicate-state flags are data-quality diagnostics, not collision alerts.
- The project is an exploratory engineering prototype, not a validated operational collision-warning or collision-avoidance service.
- Results must not be used as the sole basis for spacecraft manoeuvres or collision-avoidance decisions.

## External format reference

CelesTrak documents the supported GP formats, including TLE and OMM XML, at https://celestrak.org/NORAD/documentation/gp-data-formats.php.
