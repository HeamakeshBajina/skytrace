import Link from "next/link";

const sections = [
  ["01", "Use the dashboard", "Navigate the overview, inspect the results table, search, sort, and run instantaneous screening."],
  ["02", "TLE and OMM data", "Understand the two supported GP element formats and how SKYTRACE ingests them."],
  ["03", "Freshness and warnings", "Interpret element epochs, stale records, future epochs, and duplicate-state flags."],
  ["04", "Screening and results", "Understand instantaneous dashboard screening and the separate sampled-window CLI."],
  ["05", "Troubleshooting", "Understand HTTP 503, backend health, and unavailable fresh orbital data."],
  ["06", "Scientific limitations", "Know what the prototype does not calculate and how to interpret results responsibly."],
];

const sectionStyle = { padding: "26px 0", borderTop: "1px solid #273440" };
const paragraphStyle = { color: "#b2bfcb", lineHeight: 1.9 };
const codeStyle = { display: "block", overflowX: "auto" as const, padding: 16, borderRadius: 8, background: "#080c12", border: "1px solid #273440", color: "#bde7f3", lineHeight: 1.7, fontSize: 13 };

export default function GuidePage() {
  return (
    <main style={{ minHeight: "100vh", background: "#090d13", color: "#e8edf5", fontFamily: "Arial,sans-serif" }}>
      <header style={{ padding: "22px 6%", borderBottom: "1px solid #25303c", display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <Link href="/" style={{ color: "#dff6ff", textDecoration: "none", fontWeight: 700, letterSpacing: 2 }}>SKYTRACE / V1</Link>
        <Link href="/" style={{ color: "#9cb0c2", textDecoration: "none" }}>← Back to dashboard</Link>
      </header>
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "48px 24px 80px" }}>
        <p style={{ color: "#69cde9", fontSize: 11, letterSpacing: 3 }}>DOCUMENTATION / V1 USER GUIDE</p>
        <h1 style={{ fontSize: "clamp(34px,6vw,58px)", lineHeight: 1.1, letterSpacing: -2, margin: "12px 0" }}>SKYTRACE, explained simply.</h1>
        <p style={{ color: "#a6b4c3", fontSize: 17, lineHeight: 1.8, maxWidth: 760 }}>A practical guide to the dashboard, TLE and OMM orbital data, freshness checks, screening results, and the limits of this experimental aerospace-engineering platform.</p>
        <div style={{ margin: "28px 0", padding: 18, border: "1px solid #665333", borderRadius: 8, background: "#211b13", color: "#f0d5a5", lineHeight: 1.8 }}>
          <strong>Important:</strong> SKYTRACE is an exploratory screening prototype, not an operational collision-warning or collision-avoidance service. A healthy dashboard or backend does not guarantee that fresh orbital data is available.
        </div>
        <nav aria-label="Guide contents" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12, margin: "30px 0" }}>
          {sections.map(([number, title, description]) => (
            <a key={number} href={`#section-${number}`} style={{ padding: 17, border: "1px solid #273440", borderRadius: 8, background: "#101720", color: "#e8edf5", textDecoration: "none" }}>
              <span style={{ color: "#69cde9", fontSize: 12 }}>{number} / GUIDE</span>
              <h2 style={{ fontSize: 18, margin: "8px 0" }}>{title}</h2>
              <p style={{ fontSize: 13, lineHeight: 1.7, color: "#9cabb9", margin: 0 }}>{description}</p>
            </a>
          ))}
        </nav>
        <section id="section-01" style={sectionStyle}>
          <h2>01. Use the dashboard</h2>
          <ol style={{ lineHeight: 2, color: "#b2bfcb" }}>
            <li>Open the SKYTRACE dashboard.</li><li>Read the summary cards and note the response timestamp.</li><li>Review the closest-approach results table.</li><li>Search by object name or catalog ID.</li><li>Change the sorting order.</li><li>Select <strong>Run screening</strong> to request a new response.</li>
          </ol>
          <p style={paragraphStyle}>The dashboard's current screening action is instantaneous: it compares calculated object positions at one timestamp. It is not a future sampled-window run.</p>
        </section>
        <section id="section-02" style={sectionStyle}>
          <h2>02. Understand TLE and OMM data</h2>
          <p style={paragraphStyle}><strong>TLE (Two-Line Element):</strong> a fixed-format representation of mean orbital elements in two lines. TLE catalog identifiers are limited to five digits. SKYTRACE validates TLE structure, matching catalog identifiers, and line checksums.</p>
          <p style={paragraphStyle}><strong>OMM XML (Orbit Mean-Elements Message):</strong> a standardized XML representation of general-perturbations orbital elements and metadata. SKYTRACE parses OMM XML records and initializes SGP4 satellite objects from them. OMM can represent catalog identifiers beyond the five-digit TLE limitation.</p>
          <p style={paragraphStyle}><strong>SGP4:</strong> the propagation model used to calculate a satellite state from supported GP elements. SKYTRACE reports position in kilometres and velocity in kilometres per second, in the TEME frame.</p>
          <p style={paragraphStyle}>OMM is a format, not a guarantee of newer or more accurate orbital data. Source and epoch still matter.</p>
          <p style={paragraphStyle}>The API prefers OMM snapshots when available and retains a TLE fallback path. Snapshot retrieval time and element epoch are different.</p>
          <p><a href="https://celestrak.org/NORAD/documentation/gp-data-formats.php" style={{ color: "#69cde9" }}>CelesTrak GP data format documentation ↗</a></p>
        </section>
        <section id="section-03" style={sectionStyle}>
          <h2>03. Read freshness and data-quality warnings</h2>
          <ul style={{ color: "#b2bfcb", lineHeight: 2 }}>
            <li><strong style={{ color: "#75dfb2" }}>Fresh:</strong> element epoch is within the configured maximum age.</li>
            <li><strong style={{ color: "#f0c477" }}>Stale:</strong> element epoch is older than the configured maximum age.</li>
            <li><strong style={{ color: "#f28c8c" }}>Future epoch:</strong> element epoch is later than the reference time.</li>
            <li><strong style={{ color: "#f28c8c" }}>Invalid epoch:</strong> epoch is missing, malformed, or unsupported by time-system rules.</li>
            <li><strong style={{ color: "#c3a2ff" }}>Duplicate state:</strong> matching numerical states; a data-quality flag, not a collision alert.</li>
          </ul>
          <p style={paragraphStyle}>The default freshness threshold is six hours. The configurable range is 0.1–72 hours. A larger threshold changes inclusion; it does not improve accuracy or quantify uncertainty.</p>
          <p style={paragraphStyle}>An OMM epoch without an explicit UTC offset is interpreted as UTC only when the record declares <code>TIME_SYSTEM=UTC</code>. Explicit offsets are normalized to UTC. Unsupported naive epochs are invalid.</p>
          <p style={paragraphStyle}>A newly downloaded file can contain old orbital elements. Retrieval time is not element epoch.</p>
        </section>
        <section id="section-04" style={sectionStyle}>
          <h2>04. Understand screening and results</h2>
          <p style={paragraphStyle}><strong>Separation (km):</strong> Euclidean distance between propagated position vectors. <strong>Catalog ID:</strong> object identifier. <strong>UTC:</strong> Coordinated Universal Time. <strong>Closest separation:</strong> the smallest separation among results returned for that calculation.</p>
          <p style={paragraphStyle}><strong>Instantaneous screening</strong> propagates eligible records to one timestamp. This is what the dashboard's current Run screening action requests.</p>
          <p style={paragraphStyle}><strong>Sampled-window screening</strong> evaluates separation at discrete timestamps. Its minimum is the smallest value among samples actually evaluated, not a guaranteed continuous-time minimum.</p>
          <p style={paragraphStyle}>The TLE CLI is <code>scripts/screen_approaches.py</code>. The OMM sampled-window CLI is <code>scripts/screen_omm.py</code>.</p>
          <pre style={codeStyle}>{`python scripts/screen_omm.py --help
python scripts/screen_omm.py --data-file data/raw/<snapshot-name>.omm.xml --hours 1 --step-seconds 60`}</pre>
          <p style={paragraphStyle}>The OMM CLI accepts <code>--data-file</code> (required), <code>--hours</code>, <code>--step-seconds</code>, <code>--top</code>, <code>--max-age-hours</code>, and optional <code>--start</code>. It requires at least two fresh records.</p>
        </section>
        <section id="section-05" style={sectionStyle}>
          <h2>05. Troubleshoot unavailable screening</h2>
          <h3>HTTP 503 — insufficient fresh orbital data</h3>
          <p style={paragraphStyle}>The backend may be healthy while no available snapshot contains at least two records inside the freshness threshold. The API rejects the request rather than presenting stale data as current.</p>
          <ol style={{ color: "#b2bfcb", lineHeight: 2 }}>
            <li>Read the API error detail and freshness counts.</li><li>Check <code>/health</code> separately.</li><li>Wait for upstream orbital elements to update and retry later.</li><li>Do not repeatedly force downloads or raise the age threshold just to obtain results.</li><li>Do not treat an old result as current when a new request fails.</li>
          </ol>
          <p style={paragraphStyle}>Backend health: <a href="https://skytrace-api.onrender.com/health" style={{ color: "#69cde9" }}>https://skytrace-api.onrender.com/health</a>. A successful health response confirms that the process responds; it does not prove fresh orbital data is available.</p>
          <p style={paragraphStyle}>A free hosted backend may sleep while idle, so its first request can take longer. This is separate from stale or unavailable orbital elements.</p>
        </section>
        <section id="section-06" style={sectionStyle}>
          <h2>06. Know the scientific limitations</h2>
          <ul style={{ color: "#b2bfcb", lineHeight: 2 }}>
            <li>Instantaneous screening compares positions at one timestamp.</li><li>Sampled-window calculations inspect discrete timestamps and can miss a closer approach between samples.</li><li>TLE/OMM age alone does not measure orbital uncertainty.</li><li>SKYTRACE does not calculate collision probability.</li><li>It does not provide covariance-based uncertainty propagation or validated operational risk classification.</li><li>Duplicate-state flags are data-quality findings, not collision alerts.</li><li>Passing software tests does not independently validate predictions against operational conjunction data.</li>
          </ul>
          <div style={{ padding: 18, border: "1px solid #665333", borderRadius: 8, background: "#211b13", color: "#f0d5a5", lineHeight: 1.8 }}>
            <strong>Responsible use:</strong> SKYTRACE is an engineering and learning tool. Do not use it as the sole basis for spacecraft operations, manoeuvres, or collision-avoidance decisions.
          </div>
        </section>
        <footer style={{ paddingTop: 24, borderTop: "1px solid #273440", display: "flex", gap: 20, flexWrap: "wrap" }}>
          <Link href="/" style={{ color: "#69cde9" }}>← Return to dashboard</Link>
          <a href="https://github.com/HeamakeshBajina/skytrace/blob/main/docs/USER_GUIDE.md" style={{ color: "#69cde9" }}>Read the Markdown guide on GitHub ↗</a>
          <a href="https://github.com/HeamakeshBajina/skytrace/blob/main/docs/methodology.md" style={{ color: "#69cde9" }}>Read the methodology ↗</a>
        </footer>
      </div>
    </main>
  );
}
