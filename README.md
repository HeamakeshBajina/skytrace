# SKYTRACE

**An orbital intelligence platform for exploring Earth's orbital environment.**

SKYTRACE is an aerospace engineering project for exploring orbital data, satellite motion, and preliminary close-approach screening. Its current Python prototype retrieves and validates satellite TLE data, propagates states using SGP4, screens instantaneous and sampled-window separations, reports TLE freshness, and exposes a versioned JSON output for software integration.

> **Project status:** Working Python backend prototype. Automated tests cover the implemented functionality. The interactive Next.js website and its visualizations are planned work.

## Current capabilities

- **Orbital data:** Retrieve station TLE data and validate its structure, catalog identifiers, and checksums before saving.
- **Orbital mechanics:** Calculate idealized circular-orbit speed and period from altitude.
- **Satellite propagation:** Propagate TLE-based satellite states with SGP4 and report position and velocity in documented units.
- **Close-approach screening:** Compare object separations at a specified instant or calculate the minimum separation among sampled timestamps in a time window.
- **Data-quality checks:** Flag numerically duplicate states and report TLE epoch ages.
- **Machine-readable output:** Produce versioned JSON screening results, including catalog identifiers, settings, summary information, data-quality flags, and limitations.
- **Verification:** Run automated tests for the implemented calculations, command-line interfaces, and screening output.

## Screening methodology and limitations

Instantaneous screening compares propagated states at one timestamp. Sampled-window screening evaluates separation at discrete timestamps, including the end of the requested interval. A sampled minimum is not guaranteed to be the true continuous-time minimum.

SKYTRACE is an exploratory screening prototype, **not** an operational collision-warning service. It does not calculate collision probability or provide a validated operational risk assessment. TLE age alone does not quantify orbital uncertainty, and flagged duplicate states are data-quality findings rather than collision alerts.

See [the methodology documentation](docs/methodology.md) for the models, assumptions, and limitations.

## Requirements and quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# macOS/Linux:
# source .venv/bin/activate

python -m pip install -e ".[dev]"
pytest
```

## Examples

Calculate idealized circular-orbit parameters at an altitude of 400 km:

```bash
python -c "from skytrace.orbital_mechanics import circular_orbit; print(circular_orbit(altitude_km=400))"
```

Fetch and validate station TLE data:

```bash
python scripts/fetch_satellites.py
```

Propagate the ISS state using the latest available station TLE file:

```bash
python scripts/propagate_satellite.py
```

Run instantaneous screening with text output:

```bash
python scripts/screen_approaches.py
```

Run instantaneous screening with JSON output:

```bash
python scripts/screen_approaches.py --format json
```

Screen a one-hour window at 60-second sampling intervals:

```bash
python scripts/screen_approaches.py --hours 1 --step-seconds 60
```

Export sampled-window results as JSON:

```bash
python scripts/screen_approaches.py --hours 1 --step-seconds 60 --format json
```

The screening command also supports `--start` for an explicit ISO-8601 timestamp with a timezone, and `--top` to control how many results are returned. Use `--help` on each script to inspect its current command-line options.

## JSON output

The screening CLI supports `--format json` and emits a versioned JSON document with screening settings, UTC timestamps, TLE freshness information, units, results, data-quality flags, a summary, and limitations. Result records include object names and catalog identifiers.

Consumers should check `schema_version` and should not interpret screening results as collision probabilities or operational warnings.

## Repository structure

```text
src/skytrace/       # Scientific and application modules
scripts/            # TLE retrieval, propagation, and screening CLIs
tests/              # Automated tests
docs/               # Methodology and assumptions
data/raw/           # Retrieved TLE snapshots
.github/workflows/  # Automated test workflow
```

## Roadmap

1. Keep the backend behavior, JSON contract, and documentation aligned.
2. Complete release-readiness checks and reproducible example verification.
3. Build a polished Next.js and TypeScript website with interactive screening controls, result tables, and visualizations.
4. Integrate the website with the screening backend through a clearly defined interface.
5. Expand scientific validation, data provenance, and documented uncertainty handling.

## Engineering principles

- Prefer transparent calculations over unexplained outputs.
- Record data provenance, assumptions, timestamps, and units.
- Test scientific calculations and interfaces with reproducible cases.
- Distinguish demonstrated functionality from planned work.
- Document limitations and uncertainty.
- Never present preliminary screening as a validated collision-risk assessment.

## License

Licensed under the MIT License; see [LICENSE](LICENSE).

**SKYTRACE — Track. Analyze. Explore.**
