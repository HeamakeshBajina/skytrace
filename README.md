# SKYTRACE

**An orbital intelligence platform for exploring Earth's orbital environment.**

SKYTRACE is an aerospace engineering project exploring how orbital data, mathematical models, and interactive visualization can help people understand satellite motion and investigate potential close approaches.

> **Project status:** Early development. The capabilities below describe the intended prototype; they are not claims of completed functionality.

## Why SKYTRACE?

Earth-orbiting satellites and debris move along complex trajectories. Making sense of their motion requires reliable orbital data, calculations grounded in orbital mechanics, and visual tools that communicate results clearly. SKYTRACE aims to connect those elements in one transparent, reproducible workflow.

## Planned capabilities

- **Orbital data:** Retrieve, parse, and validate data from documented sources.
- **Orbital mechanics:** Calculate object positions and relevant orbital parameters using established models.
- **Close-approach screening:** Compare selected object trajectories and compute relative separation over a defined interval.
- **Interactive visualization:** Explore trajectories and analytical results through a clear interface.
- **Verification:** Test calculations against reference cases and document assumptions and limitations.

Close-approach screening is intended for exploratory analysis. It is not an operational collision warning or a validated collision-probability system.

## First implemented feature

The starter module calculates idealized circular-orbit speed and period from altitude using Earth's standard gravitational parameter. It is a two-body approximation and does **not** propagate real satellite orbits from TLE/OMM data.

## Quick start

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

Run a simple example:

```bash
python -c "from skytrace.orbital_mechanics import circular_orbit; print(circular_orbit(altitude_km=400))"
```

## Repository structure

```text
src/skytrace/   # Scientific and application modules
tests/          # Automated tests
docs/           # Methodology and assumptions
```

## Roadmap

1. Document a reliable orbital-data source and its limitations.
2. Add validated calculations and automated tests.
3. Implement relative-position and close-approach screening for selected objects.
4. Build an interactive visualization.
5. Publish reproducible examples and technical documentation.

## Engineering principles

- Prefer transparent calculations over unexplained outputs.
- Record data provenance, assumptions, and units.
- Test scientific calculations against independent reference cases.
- Distinguish demonstrated functionality from planned work.
- Document limitations and uncertainty.

## License

Licensed under the MIT License; see [LICENSE](LICENSE).

**SKYTRACE — Track. Analyze. Explore.**
