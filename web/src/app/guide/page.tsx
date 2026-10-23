import Link from "next/link";

const sections = [
  ["01", "Use the dashboard", "Open the dashboard, read its summary cards, inspect the table, search, sort, and run screening."],
  ["02", "Understand results", "Separation is a calculated distance in kilometres. Timestamps use UTC."],
  ["03", "Read data warnings", "Fresh, stale, future-epoch, and duplicate-state labels describe data quality."],
  ["04", "Troubleshoot", "Learn what to do when screening fails or satellite data is stale."],
  ["05", "Know the limits", "SKYTRACE is a preliminary engineering tool, not an operational collision-warning system."],
];

export default function GuidePage() {
  return (
    <main style={{minHeight:"100vh",background:"#090d13",color:"#e8edf5",fontFamily:"Arial,sans-serif"}}>
      <header style={{padding:"22px 6%",borderBottom:"1px solid #25303c",display:"flex",justifyContent:"space-between",gap:16,flexWrap:"wrap"}}>
        <Link href="/" style={{color:"#dff6ff",textDecoration:"none",fontWeight:700,letterSpacing:2}}>SKYTRACE / V1</Link>
        <Link href="/" style={{color:"#9cb0c2",textDecoration:"none"}}>← Back to dashboard</Link>
      </header>
      <div style={{maxWidth:1000,margin:"0 auto",padding:"48px 24px 80px"}}>
        <p style={{color:"#69cde9",fontSize:11,letterSpacing:3}}>DOCUMENTATION / USER GUIDE</p>
        <h1 style={{fontSize:"clamp(34px,6vw,58px)",lineHeight:1.1,letterSpacing:-2,margin:"12px 0"}}>SKYTRACE, explained simply.</h1>
        <p style={{color:"#a6b4c3",fontSize:17,lineHeight:1.8,maxWidth:720}}>A beginner-friendly guide to using the dashboard, understanding the numbers, and knowing when to be cautious.</p>
        <div style={{margin:"28px 0",padding:18,border:"1px solid #315165",borderRadius:8,background:"#101f2b",lineHeight:1.7}}>
          <strong>New here?</strong> Start with the quick guide below. You do not need to know orbital mechanics to understand the dashboard basics.
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:12,margin:"30px 0"}}>
          {sections.map(([number,title,description]) => <a key={number} href={`#section-${number}`} style={{padding:17,border:"1px solid #273440",borderRadius:8,background:"#101720",color:"#e8edf5",textDecoration:"none"}}><span style={{color:"#69cde9",fontSize:12}}>{number} / GUIDE</span><h2 style={{fontSize:18,margin:"8px 0"}}>{title}</h2><p style={{fontSize:13,lineHeight:1.7,color:"#9cabb9",margin:0}}>{description}</p></a>)}
        </div>
        <section id="section-01" style={{padding:"24px 0",borderTop:"1px solid #273440"}}><h2>01. Use the dashboard</h2><ol style={{lineHeight:2,color:"#b2bfcb"}}><li>Open the Mission overview.</li><li>Read the summary cards.</li><li>Search the results table by name or catalog ID.</li><li>Change the sorting order to inspect the results.</li><li>Select Run screening to request a new response.</li></ol><p style={{color:"#9cabb9",lineHeight:1.8}}>The dashboard currently requests instantaneous screening: it compares calculated positions at one timestamp.</p></section>
        <section id="section-02" style={{padding:"24px 0",borderTop:"1px solid #273440"}}><h2>02. Understand the results</h2><p style={{color:"#b2bfcb",lineHeight:1.9}}><strong>Separation (km):</strong> calculated distance between two object positions. <strong>Catalog ID:</strong> identifier for an object. <strong>UTC:</strong> a shared global time standard. <strong>SGP4:</strong> the mathematical model used to estimate positions from orbital data.</p></section>
        <section id="section-03" style={{padding:"24px 0",borderTop:"1px solid #273440"}}><h2>03. Read data warnings</h2><ul style={{color:"#b2bfcb",lineHeight:2}}><li><strong style={{color:"#75dfb2"}}>Fresh:</strong> TLE epoch is within the six-hour reporting threshold.</li><li><strong style={{color:"#f0c477"}}>Stale:</strong> TLE epoch is older than six hours; review the data.</li><li><strong style={{color:"#f28c8c"}}>Future epoch:</strong> epoch is later than the screening reference time.</li><li><strong style={{color:"#c3a2ff"}}>Duplicate state:</strong> matching numerical states; this is not a collision alert.</li></ul><p style={{color:"#9cabb9",lineHeight:1.8}}>Download time and TLE epoch are different. A newly downloaded file can contain older orbital elements.</p></section>
        <section id="section-04" style={{padding:"24px 0",borderTop:"1px solid #273440"}}><h2>04. Troubleshoot screening</h2><p style={{color:"#b2bfcb",lineHeight:1.9}}>If screening returns HTTP 503, wait briefly and try again. Check the <a href="https://skytrace-api.onrender.com/health" style={{color:"#69cde9"}}>backend health endpoint</a>. If health is OK but screening still fails, the data-refresh or screening path may be unavailable. Do not assume an old result is current. The free backend may sleep while idle, so the first request can take longer.</p><p style={{color:"#b2bfcb",lineHeight:1.9}}>Many stale records mean their TLE epochs are older than the reporting threshold; it does not mean a collision is happening.</p></section>
        <section id="section-05" style={{padding:"24px 0",borderTop:"1px solid #273440"}}><h2>05. Know the limitations</h2><ul style={{color:"#b2bfcb",lineHeight:2}}><li>Instantaneous screening compares positions at one time.</li><li>Sampled-window calculations can miss a closer approach between sample times.</li><li>TLE age alone does not measure orbital uncertainty.</li><li>SKYTRACE does not calculate collision probability.</li><li>It is not a validated operational collision-warning or collision-avoidance system.</li></ul><div style={{padding:18,border:"1px solid #665333",borderRadius:8,background:"#211b13",color:"#f0d5a5",lineHeight:1.8}}><strong>Use SKYTRACE as an engineering and learning tool.</strong><br/>Do not use it as the sole basis for real spacecraft operations or collision-avoidance decisions.</div></section>
        <footer style={{paddingTop:24,borderTop:"1px solid #273440",display:"flex",gap:20,flexWrap:"wrap"}}><Link href="/" style={{color:"#69cde9"}}>← Return to dashboard</Link><a href="https://github.com/HeamakeshBajina/skytrace/blob/main/docs/USER_GUIDE.md" style={{color:"#69cde9"}}>Read the Markdown guide on GitHub ↗</a></footer>
      </div>
    </main>
  );
}