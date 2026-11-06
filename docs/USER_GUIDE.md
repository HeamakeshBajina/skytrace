# SKYTRACE V1 — User Guide

Welcome to SKYTRACE. This guide explains the dashboard, orbital-data formats, screening results, freshness warnings, and the limits of the current prototype.

## 1. What is SKYTRACE?

SKYTRACE is an experimental aerospace-engineering project for exploring Earth's orbital environment. It ingests general-perturbations (GP) orbital elements, initializes SGP4 propagators, calculates object states, and compares geometric separation between object pairs.

SKYTRACE includes TLE and OMM XML data paths. The dashboard's current screening action is instantaneous. A separate command-line tool supports sampled-window OMM screening.

SKYTRACE is a learning and research prototype, not an operational collision-warning or collision-avoidance system.

## 2. Open and use the dashboard

1. Open https://skytrace-gamma.vercel.app/
2. Wait for the dashboard to load.
3. Read the summary cards and note the timestamp associated with the response.
4. Review the closest-approach results table.
5. Search by object name or catalog ID.
6. Change the sorting order.
7. Select **Run screening** to request a new response.

The dashboard currently requests **instantaneous screening**: it compares calculated positions at one timestamp. It does not request a future sampled-window prediction.

## 3. Understand TLE and OMM data

### TLE

A Two-Line Element set stores mean orbital elements in two fixed-format lines. TLE catalog identifiers are limited to five digits. SKYTRACE validates TLE structure, matching catalog identifiers, and line checksums.

### OMM XML

An Orbit Mean-Elements Message (OMM) is a standardized representation of GP orbital elements and related metadata. SKYTRACE's OMM path downloads XML, parses records, initializes SGP4 satellite objects, and reads each element epoch.

OMM can represent catalog identifiers beyond the five-digit TLE limitation. OMM is a data format, not a promise of newer or more accurate orbital information. The source and epoch still matter.

### SGP4

SGP4 is the propagation model used to calculate a satellite state from supported GP elements. SKYTRACE reports position in kilometres and velocity in kilometres per second in the TEME frame.

## 4. Understand freshness and data-quality labels

SKYTRACE evaluates the **element epoch**, not just the time a file was downloaded.

- **Fresh:** The element epoch is within the configured maximum age.
- **Stale:** The element epoch is older than the configured maximum age.
- **Future epoch:** The element epoch is later than the reference time.
- **Invalid epoch:** The epoch is missing, malformed, or cannot be interpreted under supported time-system rules.
- **Duplicate state:** Two records produce matching numerical states. This is a data-quality finding, not a collision alert.

The default maximum age is six hours. The configurable range is 0.1–72 hours. Changing the threshold changes which records are admitted; it does not improve their accuracy or quantify uncertainty.

For OMM epochs without an explicit UTC offset, SKYTRACE interprets the value as UTC only when the record declares `TIME_SYSTEM=UTC`. Explicit timezone offsets are normalized to UTC. Naive epochs without a supported UTC declaration are rejected.

A recently downloaded file can contain old orbital elements. Retrieval time and element epoch are different.

## 5. Understand screening results

- **Objects loaded:** Objects included in the screening input.
- **Pairs evaluated:** Object pairs examined by the calculation.
- **Separation (km):** Euclidean distance between two propagated position vectors.
- **Closest separation:** The smallest separation among results returned for the selected calculation.
- **Screening time:** The timestamp associated with an instantaneous calculation, or the sampled timestamp associated with a sampled-window minimum.
- **Data-quality flags:** Warnings that should be reviewed before interpreting results.

Instantaneous screening compares states at one timestamp. Sampled-window screening checks discrete timestamps across an interval. Its reported minimum is only the smallest value among those samples; a closer approach between sample times may be missed.

The dashboard's current Run screening action is instantaneous. The separate `scripts/screen_omm.py` command provides sampled-window OMM screening.

## 6. Run OMM sampled-window screening

First obtain an OMM XML snapshot using the project's fetcher. Then run:

```powershell
python scripts/screen_omm.py --help
python scripts/screen_omm.py --data-file data/raw/<snapshot-name>.omm.xml --hours 1 --step-seconds 60
```

Options include:

- `--data-file`: OMM XML snapshot to screen (required).
- `--hours`: Requested screening-window duration.
- `--step-seconds`: Time between sampled evaluations.
- `--top`: Maximum number of results to display.
- `--max-age-hours`: Maximum accepted OMM epoch age; default six hours.
- `--start`: Optional explicit start timestamp.

The script requires at least two fresh records. If fewer than two are available, it stops rather than running a misleading screening calculation.

## 7. Freshness configuration

The API/TLE freshness threshold defaults to six hours and can be configured before starting the backend:

```powershell
$env:SKYTRACE_MAX_TLE_AGE_HOURS = "6"
```

The accepted range is 0.1–72 hours. The OMM CLI also accepts `--max-age-hours`. Use the default unless you have a documented reason to evaluate another threshold. A more permissive threshold is not a substitute for fresh data.

## 8. API and troubleshooting

### Health endpoint

Open https://skytrace-api.onrender.com/health or request the local backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

A healthy response confirms that the backend process is responding. It does not confirm that a usable fresh orbital snapshot exists.

### HTTP 503 — insufficient fresh data

The API can return HTTP 503 when no discovered snapshot contains at least two records inside the configured freshness threshold. The response may report fresh, stale, future-epoch, and invalid-epoch counts.

1. Read the response detail and freshness counts.
2. Check `/health` separately.
3. Avoid repeatedly forcing downloads; upstream GP data may not have new element epochs yet.
4. Retry later according to any backend retry/cooldown message.
5. Do not increase the freshness threshold merely to make screening return results.
6. Never treat a previous response as current when a new screening request fails.

### Backend healthy but screening fails

The service can be running while all available orbital elements are stale or invalid. Process health and fresh data availability are separate conditions.

### Many records are stale

This means their element epochs are older than the configured threshold. It is a data-quality condition, not evidence that a collision is happening.

### Two objects appear extremely close

Review epochs, timestamps, data provenance, and quality flags. Separation alone is not a collision prediction.

## 9. Important limitations and responsible use

- Instantaneous screening compares positions at one timestamp.
- Sampled-window calculations inspect discrete timestamps and can miss a closer approach between samples.
- TLE/OMM age alone does not measure orbital uncertainty.
- SKYTRACE does not calculate collision probability.
- It does not provide covariance-based uncertainty propagation or validated operational risk classification.
- Duplicate-state flags are data-quality findings, not collision alerts.
- Passing software tests does not independently validate orbital predictions against operational conjunction data.

Do not use SKYTRACE as the sole basis for real spacecraft operations, manoeuvres, or collision-avoidance decisions.

## Links

- [SKYTRACE dashboard](https://skytrace-gamma.vercel.app/)
- [Backend health](https://skytrace-api.onrender.com/health)
- [GitHub repository](https://github.com/HeamakeshBajina/skytrace)
- [CelesTrak GP data formats](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [Deployment documentation](../DEPLOYMENT.md)
- [Methodology](methodology.md)
