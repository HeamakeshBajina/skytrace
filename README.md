# SKYTRACE

**An orbital intelligence platform for exploring Earth's orbital environment.**

SKYTRACE is an experimental aerospace-engineering platform for inspecting general-perturbations orbital data, propagating satellite states with SGP4, and performing preliminary geometric close-approach screening. The project includes a Python backend and a Next.js dashboard.

> **V1 status:** SKYTRACE supports TLE and OMM XML ingestion paths, freshness checks, SGP4 state propagation, instantaneous screening, and a separate sampled-window OMM screening CLI. The dashboard's current screening action is instantaneous. Live screening availability depends on receiving enough orbital records that meet the configured freshness threshold.

## Current capabilities

- **TLE ingestion:** Retrieve station TLE data and validate structure, catalog identifiers, and line checksums.
- **OMM XML ingestion:** Retrieve CelesTrak GP data in OMM XML format, parse records, and initialize SGP4 satellite objects.
- **Snapshot selection:** Prefer OMM snapshots where available, with a TLE fallback path.
- **Orbital mechanics:** Calculate idealized circular-orbit speed and period from altitude.
- **SGP4 propagation:** Propagate supported TLE and OMM records and report position and velocity in the TEME frame, in kilometres and kilometres per second.
- **Freshness controls:** Classify records by element epoch as fresh, stale, future, or invalid. The default maximum age is six hours.
- **Instantaneous screening:** Compare pairwise propagated positions at one timestamp.
- **Sampled-window OMM screening:** Evaluate pairwise separation at discrete timestamps using `scripts/screen_omm.py`.
- **Data-quality checks:** Flag duplicate numerical states and reject insufficiently fresh inputs rather than presenting stale results as current.
- **Machine-readable output:** The TLE screening CLI produces versioned JSON with settings, timestamps, units, results, data-quality findings, and limitations.

## Data freshness

A snapshot's retrieval time is not the same as the epoch of the orbital elements inside it. Downloading an old element set again does not make its epoch newer.

The default freshness threshold is six hours. The API/TLE path reads `SKYTRACE_MAX_TLE_AGE_HOURS`; the OMM screening CLI accepts `--max-age-hours`. The accepted configurable range is 0.1 to 72 hours. A larger threshold changes the inclusion rule; it does not improve the underlying orbit data or certify its accuracy.

When fewer than two eligible records are available, SKYTRACE safely refuses to run the corresponding screening operation. HTTP 503 in this situation indicates insufficient fresh input data; it does not by itself indicate that the backend process is down. Check `/health` separately.

## Requirements and quick start

Requires Python 3.10 or newer. The frontend uses Node.js and npm.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run the backend from the repository root:

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Run the frontend in another terminal:

```powershell
Set-Location .\web
npm install
npm run dev
```

Check `web/.env.local` and the existing deployment configuration for the frontend API proxy URL. Do not expose credentials or private tokens through `NEXT_PUBLIC_` variables.

## Data ingestion and CLI examples

Fetch and validate station TLE data:

```powershell
python scripts/fetch_satellites.py
```

Run instantaneous TLE screening:

```powershell
python scripts/screen_approaches.py
python scripts/screen_approaches.py --format json
```

Run sampled-window TLE screening:

```powershell
python scripts/screen_approaches.py --hours 1 --step-seconds 60
python scripts/screen_approaches.py --hours 1 --step-seconds 60 --format json
```

Run sampled-window OMM screening against an existing OMM XML snapshot:

```powershell
python scripts/screen_omm.py --data-file data/raw/<snapshot-name>.omm.xml --hours 1 --step-seconds 60
```

The OMM CLI accepts `--data-file`, `--hours`, `--step-seconds`, `--top`, `--max-age-hours`, and `--start`. Consult `python scripts/screen_omm.py --help` for the exact options in the installed revision. It requires at least two eligible fresh records.

## API

- `GET /health` — backend process health.
- `GET /api/orbits` — dashboard orbital data, subject to snapshot discovery and freshness validation.
- `GET /api/screening` — dashboard screening response, currently instantaneous and subject to safe data checks.

The API can return HTTP 503 when no usable snapshot contains at least two fresh records, or when refresh is temporarily in a retry cooldown. Inspect the response detail and `/health` separately. A healthy process does not prove fresh orbital data is available.

## Scientific methodology and limitations

The circular-orbit calculator is an idealized two-body model; it is separate from SGP4 propagation of real GP element records. TLE and OMM are representations of GP elements used with SGP4; OMM is not inherently more accurate merely because it is XML.

Instantaneous screening compares positions at one timestamp. Sampled-window screening reports the smallest separation among timestamps actually sampled. A sampled minimum is not guaranteed to be the continuous-time minimum, and a closer event between samples may be missed.

SKYTRACE does not calculate collision probability, covariance-based uncertainty propagation, or an operational collision-risk classification. Element age alone does not quantify orbit uncertainty. Duplicate-state findings are data-quality diagnostics, not collision alerts. SKYTRACE is an educational and engineering prototype, not an operational collision-warning or collision-avoidance service. Do not use it as the sole basis for spacecraft operations or manoeuvre decisions.

See [the user guide](docs/USER_GUIDE.md) and [the methodology](docs/methodology.md).

## Repository structure

```text
api.py                  # FastAPI service
src/skytrace/            # Orbital and time-window helpers
scripts/                 # TLE/OMM ingestion and screening CLIs
web/                     # Next.js dashboard and in-app guide
tests/                   # Automated tests
docs/                    # User guide and methodology
data/raw/                # Retrieved orbital-data snapshots
```

## Verification

```powershell
python -m pytest -q
python -m compileall -q .\src .\scripts .\tests .\api.py
npm --prefix .\web run build
```

Passing tests and builds demonstrate that tested software paths meet their test expectations. They do not independently validate orbital predictions against operational conjunction data.

## Data source

The current ingestion implementation uses CelesTrak GP data services for station-group TLE and OMM XML data. Review the [CelesTrak GP data format documentation](https://celestrak.org/NORAD/documentation/gp-data-formats.php) and usage policy before automating requests. Space-Track is an optional fetcher path when credentials are configured.

## License

Licensed under the MIT License; see [LICENSE](LICENSE).

**SKYTRACE — Track. Analyze. Explore.**
