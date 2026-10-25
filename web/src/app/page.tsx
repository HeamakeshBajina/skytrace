"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type ScreeningResult = {
  object_a: string;
  catalog_id_a: string;
  object_b: string;
  catalog_id_b: string;
  separation_km: number;
  time_utc: string;
  method?: string;
};

type ScreeningData = {
  schema_version?: string;
  product?: string;
  generated_at_utc?: string;
  data_file?: string;
  screening: {
    mode: string;
    start_utc?: string;
    hours: number;
    step_seconds: number | null;
    top: number;
    input_objects: number;
  };
  tle_freshness?: {
    records?: { object?: string; age_hours?: number; status?: string }[];
    fresh_records?: number;
    stale_records?: number;
    max_age_hours?: number;
    youngest_age_hours?: number | null;
    oldest_age_hours?: number | null;
    future_epoch_objects?: string[];
    uncertainty_note?: string;
  };
  units?: { separation?: string };
  results: ScreeningResult[];
  data_quality_flags?: unknown[];
  summary: {
    objects_propagated?: number;
    pairs_evaluated?: number;
    duplicate_state_pairs?: number;
    results_returned?: number;
  };
  limitations?: string[];
};

type TableRow = ScreeningResult & { separation: number };

function formatNumber(value: number | undefined, digits = 0) {
  if (value === undefined || !Number.isFinite(value)) return "—";
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function formatUtc(value?: string) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toISOString().replace("T", " ").replace(".000Z", " UTC").replace("Z", " UTC");
}

function OrbitScene() {
  return (
    <div className="orbit-scene" aria-label="Illustrative orbital visualization">
      <div className="orbit-glow" />
      <div className="orbit-ring orbit-ring-one" />
      <div className="orbit-ring orbit-ring-two" />
      <div className="orbit-ring orbit-ring-three" />
      <div className="orbit-earth">
        <div className="earth-land earth-land-one" />
        <div className="earth-land earth-land-two" />
      </div>
      <span className="orbit-satellite orbit-satellite-one">✦</span>
      <span className="orbit-satellite orbit-satellite-two">✦</span>
      <span className="orbit-satellite orbit-satellite-three">✦</span>
      <div className="orbit-caption">
        <span className="status-dot" />
        ORBITAL OVERVIEW
        <span className="orbit-caption-note">Illustrative · Not to scale</span>
      </div>
    </div>
  );
}

function formatQualityFlag(flag: unknown): string {
  if (typeof flag === "string") return flag;
  if (flag === null || flag === undefined) return String(flag);
  if (typeof flag === "number" || typeof flag === "boolean") return String(flag);

  if (typeof flag === "object") {
    const item = flag as Record<string, unknown>;
    const type = typeof item.type === "string" ? item.type : "Data quality flag";
    const classification =
      typeof item.classification === "string" ? item.classification : "";
    const objectA =
      typeof item.object_a === "string" ? item.object_a : "";
    const objectB =
      typeof item.object_b === "string" ? item.object_b : "";
    const position =
      typeof item.position_difference_km === "number"
        ? `${item.position_difference_km} km position difference`
        : "";
    const velocity =
      typeof item.velocity_difference_km_s === "number"
        ? `${item.velocity_difference_km_s} km/s velocity difference`
        : "";

    const details = [
      classification,
      objectA && objectB ? `${objectA} / ${objectB}` : "",
      position,
      velocity,
    ].filter(Boolean);

    return details.length ? `${type}: ${details.join(" · ")}` : `${type}: ${JSON.stringify(flag)}`;
  }

  return String(flag);
}
export default function Home() {
  const [data, setData] = useState<ScreeningData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sortAscending, setSortAscending] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/screening?top=200", {
        cache: "no-store",
      });

      const payload: unknown = await response.json();

      if (!response.ok) {
        const message =
          typeof payload === "object" &&
          payload !== null &&
          "detail" in payload &&
          typeof payload.detail === "string"
            ? payload.detail
            : "The screening API returned an error.";
        throw new Error(message);
      }

      const result = payload as ScreeningData;

      if (!result.screening || !Array.isArray(result.results) || !result.summary) {
        throw new Error("The API response did not match the expected SKYTRACE JSON schema.");
      }

      setData(result);
      setLastUpdated(new Date().toISOString());
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Could not load screening results.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [refresh]);

  const rows = useMemo<TableRow[]>(() => {
    if (!data) return [];

    const normalized = query.trim().toLowerCase();

    return data.results
      .map((row) => ({ ...row, separation: Number(row.separation_km) }))
      .filter((row) => {
        if (!normalized) return true;
        return [
          row.object_a,
          row.catalog_id_a,
          row.object_b,
          row.catalog_id_b,
          row.time_utc,
        ].some((value) => String(value ?? "").toLowerCase().includes(normalized));
      })
      .sort((a, b) =>
        sortAscending
          ? a.separation - b.separation
          : b.separation - a.separation
      );
  }, [data, query, sortAscending]);

  const freshness = data?.tle_freshness;
  const flags = data?.data_quality_flags ?? [];
  const isWindow = data?.screening.mode === "sampled_window";
  const staleCount = freshness?.stale_records ?? freshness?.records?.filter((record) => record.status === "stale").length ?? 0;
  const totalFreshnessRecords = freshness?.records?.length ?? data?.screening.input_objects ?? 0;
  const allEpochsStale = totalFreshnessRecords > 0 && staleCount >= totalFreshnessRecords;

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="SKYTRACE home">
          <span className="brand-mark">S</span>
          <span className="brand-copy">
            <strong>SKYTRACE</strong>
            <small>SPACE DOMAIN AWARENESS</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview">
          <span className="nav-icon">◈</span> Mission overview
        </a>
        <a className="nav-item" href="#screening">
          <span className="nav-icon">⌕</span> Close approaches
        </a>
        <a className="nav-item" href="#data-quality">
          <span className="nav-icon">◎</span> Data quality
        </a>
        <a className="nav-item" href="/guide">
          <span className="nav-icon">?</span> User Guide
        </a>

        <div className="sidebar-bottom">
          <div className="connection-indicator">
            <span className={`status-dot ${data ? "" : "status-dot-muted"}`} />
            <div>
              <strong>{data ? "Engine connected" : "Engine unavailable"}</strong>
              <small>Python · SGP4 propagation</small>
            </div>
          </div>
          <div className="sidebar-version">SKYTRACE / EARTH ORBIT</div>
        </div>
      </aside>

      <section className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> Mission overview</div>
          <div className="topbar-right">
            <span className="live-indicator"><span className="status-dot" /> LIVE API</span>
            <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
              <span className={loading ? "spin" : ""}>↻</span>
              {loading ? "Screening…" : "Run screening"}
            </button>
          </div>
        </header>

        <div className="page-heading">
          <div>
            <div className="eyebrow">SPACE SITUATIONAL AWARENESS</div>
            <h1>Mission overview<span className="heading-period">.</span></h1>
            <p className="page-subtitle">
              Orbital proximity monitoring powered by your local SGP4 screening engine.
            </p>
          </div>
          <div className="updated-label">
            <span className="status-dot" />
            {loading ? "Updating screening" : "On-demand screening"}
            <small>{lastUpdated ? `Fetched ${formatUtc(lastUpdated)}` : "Awaiting first response"}</small>
          </div>
        </div>

        {freshness && staleCount > 0 && (
          <section className="stale-data-banner" role="alert" aria-live="polite">
            <div className="stale-data-icon" aria-hidden="true">!</div>
            <div>
              <strong>
                {allEpochsStale ? "All orbital data is stale" : "Some orbital data is stale"}
              </strong>
              <p>
                {staleCount} of {totalFreshnessRecords} records exceed the {formatNumber(freshness.max_age_hours ?? 6)}-hour TLE epoch threshold.
                {freshness.oldest_age_hours != null
                  ? ` Oldest orbital epoch: ${formatNumber(freshness.oldest_age_hours, 1)} hours.`
                  : ""}
                {" "}Results are for engineering and learning purposes, not operational collision-avoidance decisions.
              </p>
            </div>
          </section>
        )}

        {error && (
          <section className="error-banner" role="alert">
            <div>
              <strong>Screening could not be loaded</strong>
              <p>{error}</p>
              <small>Check that the Python environment, TLE data and Next.js server are available.</small>
            </div>
            <button className="refresh-button" onClick={() => void refresh()}>Retry</button>
          </section>
        )}

        <section className="metrics-grid" aria-label="Live screening metrics">
          <article className="metric-card">
            <div className="metric-top"><span>OBJECTS LOADED</span><span className="metric-icon">◉</span></div>
            <div className="metric-value">{data ? formatNumber(data.screening.input_objects) : "—"}</div>
            <div className="metric-foot">Objects in screening input</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>PAIR CANDIDATES</span><span className="metric-icon">⌕˜</span></div>
            <div className="metric-value">{data ? formatNumber(data.summary.pairs_evaluated) : "—"}</div>
            <div className="metric-foot">All possible object pairs</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>CLOSEST SEPARATION</span><span className="metric-icon">↔</span></div>
            <div className="metric-value">
              {data?.results.length ? formatNumber(Math.min(...data.results.map((row) => row.separation_km)), 2) : "—"}
              <span className="metric-unit">km</span>
            </div>
            <div className="metric-foot">Minimum returned separation</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>DATA QUALITY FLAGS</span><span className="metric-icon">△</span></div>
            <div className="metric-value">{data ? formatNumber(flags.length) : "—"}</div>
            <div className="metric-foot">{flags.length ? "Review required" : "Reported by engine"}</div>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel orbit-panel">
            <div className="panel-heading">
              <div><div className="eyebrow">VISUAL CONTEXT</div><h2>Orbital overview</h2></div>
              <span className="panel-tag">SCHEMATIC</span>
            </div>
            <OrbitScene />
            <div className="orbit-legend">
              <span><i className="legend-dot legend-blue" /> Earth</span>
              <span><i className="legend-dot legend-cyan" /> Orbital paths</span>
              <span><i className="legend-dot legend-white" /> Markers</span>
            </div>
            <p className="muted-note">This illustration is not generated from the current TLE states. Live 3D orbit rendering is a future integration.</p>
          </article>

          <article className="panel status-panel" id="data-quality">
            <div className="panel-heading">
              <div><div className="eyebrow">ENGINE STATUS</div><h2>Screening health</h2></div>
              <span className={`health-pill ${data && !error ? "health-ok" : "health-warn"}`}>
                {data && !error ? "CONNECTED" : "CHECK"}
              </span>
            </div>

            <div className="status-row">
              <span>Propagation engine</span><strong>{data ? "SGP4" : "—"}</strong>
            </div>
            <div className="status-row">
              <span>Screening mode</span><strong>{data ? (isWindow ? "Sampled window" : "Instantaneous") : "—"}</strong>
            </div>
            <div className="status-row">
              <span>TLE youngest age</span><strong>{freshness?.youngest_age_hours != null ? `${formatNumber(freshness.youngest_age_hours, 1)} h` : "—"}</strong>
            </div>
            <div className="status-row">
              <span>TLE oldest age</span><strong>{freshness?.oldest_age_hours != null ? `${formatNumber(freshness.oldest_age_hours, 1)} h` : "—"}</strong>
            </div>
            <div className="status-row">
              <span>Returned results</span><strong>{data ? formatNumber(data.summary.results_returned ?? data.results.length) : "—"}</strong>
            </div>
            <div className="status-row">
              <span>Duplicate-state pairs</span><strong>{data ? formatNumber(data.summary.duplicate_state_pairs) : "—"}</strong>
            </div>
            {freshness?.uncertainty_note && (
              <div className="uncertainty-note">{freshness.uncertainty_note}</div>
            )}
          </article>
        </section>

        <section className="panel screening-panel" id="screening">
          <div className="panel-heading screening-heading">
            <div>
              <div className="eyebrow">PAIRWISE PROXIMITY ANALYSIS</div>
              <h2>Closest approaches</h2>
              <p className="panel-subtitle">Sorted by reported separation · Distances in kilometres</p>
            </div>
            <div className="table-controls">
              <input
                className="search-input"
                type="search"
                placeholder="Search objects or catalog IDs…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                aria-label="Search close approaches"
              />
              <button className="sort-button" onClick={() => setSortAscending((value) => !value)}>
                {sortAscending ? "Nearest first (ascending)" : "Farthest first (descending)"}
              </button>
            </div>
          </div>

          <div className="table-meta">
            <span>{loading ? "Running engine…" : `${rows.length} of ${data?.results.length ?? 0} results shown`}</span>
            <span>{data ? `Generated ${formatUtc(data.generated_at_utc)}` : "Waiting for API"}</span>
          </div>

          <div className="table-scroll">
            <table className="approach-table">
              <thead>
                <tr>
                  <th>OBJECT A</th><th>OBJECT B</th><th>SEPARATION</th><th>SCREENING TIME (UTC)</th><th>METHOD</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={`${row.catalog_id_a}-${row.catalog_id_b}-${row.time_utc}-${index}`}>
                    <td><div className="object-name">{row.object_a}</div><div className="object-id">CAT {row.catalog_id_a}</div></td>
                    <td><div className="object-name">{row.object_b}</div><div className="object-id">CAT {row.catalog_id_b}</div></td>
                    <td><span className="separation-value">{formatNumber(row.separation, 3)} <small>km</small></span></td>
                    <td className="time-cell">{formatUtc(row.time_utc)}</td>
                    <td><span className="method-tag">{row.method ?? (isWindow ? "Sampled SGP4" : "Instant SGP4")}</span></td>
                  </tr>
                ))}
                {!loading && rows.length === 0 && (
                  <tr><td colSpan={5} className="empty-state">{error ? "No data available. Fix the API error and retry." : "No matching results for this search."}</td></tr>
                )}
                {loading && !data && (
                  <tr><td colSpan={5} className="empty-state">Waiting for the Python screening engine…</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="table-footer">
            <span>Source: {data?.data_file ?? "Awaiting TLE data"}</span>
            <span>Computed locally · SGP4</span>
          </div>
        </section>

        <section className="panel limitations-panel">
          <div className="panel-heading">
            <div><div className="eyebrow">SCIENTIFIC INTERPRETATION</div><h2>Data quality & limitations</h2></div>
          </div>
          <div className="limitations-grid">
            {(data?.limitations ?? [
              "Results are unavailable until the Python screening engine responds.",
              "TLE freshness and orbital uncertainty must be considered when interpreting separation.",
              "This system does not yet calculate collision probability or operational risk.",
            ]).map((item, index) => (
              <div className="limitation-item" key={`${index}-${item}`}>
                <span className="limitation-number">{String(index + 1).padStart(2, "0")}</span>
                <p>{item}</p>
              </div>
            ))}
          </div>
          {flags.length > 0 && (
            <div className="quality-flags">
              <strong>Engine data-quality flags</strong>
              <ul>{flags.map((flag, index) => <li key={`${index}-${formatQualityFlag(flag)}`}>{formatQualityFlag(flag)}</li>)}</ul>
            </div>
          )}
          {freshness?.future_epoch_objects && freshness.future_epoch_objects.length > 0 && (
            <div className="quality-flags">
              <strong>Objects with future TLE epochs</strong>
              <p>{freshness.future_epoch_objects.join(", ")}</p>
            </div>
          )}
        </section>

        <footer className="page-footer">
          <span>SKYTRACE <span className="footer-separator">/</span> SPACE DOMAIN AWARENESS</span>
          <span>Live local screening · Not operational collision-avoidance guidance</span>
        </footer>
      </section>
    </main>
  );
}
