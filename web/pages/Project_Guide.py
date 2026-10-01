"""A plain-language guide to the AeroLand mission-control project."""

from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="AeroLand | Project Guide",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


GUIDE_CSS = """
<style>
:root {
  --guide-bg: #000205;
  --guide-panel: #05090e;
  --guide-panel-2: #080f17;
  --guide-line: #292825;
  --guide-line-bright: #4a463e;
  --guide-text: #f3f0e8;
  --guide-muted: #aaa69d;
  --guide-gold: #f0b95a;
  --guide-green: #6fdc9b;
  --guide-purple: #c8a7ff;
  --guide-red: #ff6078;
}

html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
  color: var(--guide-text);
  background-color: var(--guide-bg);
  background-image:
    radial-gradient(circle, rgba(240,250,255,.46) 0 .65px, transparent .85px),
    radial-gradient(circle, rgba(240,185,90,.32) 0 .55px, transparent .8px),
    radial-gradient(circle, rgba(168,137,255,.25) 0 .65px, transparent .9px),
    radial-gradient(ellipse at 82% -12%, rgba(36,88,128,.2), transparent 38%),
    linear-gradient(180deg, #02060a 0%, #000205 52%, #000 100%);
  background-size: 83px 83px, 137px 137px, 211px 211px, auto, auto;
  background-position: 7px 13px, 43px 71px, 111px 29px, center, center;
  background-attachment: fixed;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebarNav"] { display: none; }
.block-container { max-width: 1480px; padding: 1.4rem 2.4rem 4rem; }

[data-testid="stSidebar"] {
  width: 346px !important;
  background: linear-gradient(180deg, rgba(4,9,14,.985), rgba(0,2,5,.99));
  border-right: 1px solid var(--guide-line);
}
[data-testid="stSidebar"] > div:first-child { width: 346px !important; }
[data-testid="stSidebar"] .block-container { padding: 1.35rem 1.4rem 2rem; }
[data-testid="stSidebar"] hr { border-color: var(--guide-line); margin: 1.15rem 0; }

[data-testid="stPageLink"] { margin: .28rem 0; }
[data-testid="stPageLink"] a,
a[data-testid="stPageLink-NavLink"] {
  min-height: 2.45rem; padding: .6rem .72rem; border: 1px solid var(--guide-line);
  border-radius: 2px; background: rgba(8,15,23,.72); color: var(--guide-text) !important;
  font: 650 .72rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .08em; text-transform: uppercase; text-decoration: none;
}
[data-testid="stPageLink"] a:hover,
a[data-testid="stPageLink-NavLink"]:hover {
  border-color: var(--guide-gold); background: rgba(240,185,90,.08);
}

.brand-lockup { padding: .15rem 0 1.2rem; }
.brand-mark {
  display: inline-grid; place-items: center; width: 34px; height: 34px;
  margin-right: 10px; border: 1px solid var(--guide-gold); color: var(--guide-gold);
  font: 700 18px/1 ui-monospace, monospace; transform: rotate(45deg);
  box-shadow: 0 0 26px rgba(240,185,90,.16); vertical-align: middle;
}
.brand-mark > span { transform: rotate(-45deg); }
.brand-name { display:inline-block; vertical-align:middle; font-size:1.02rem; font-weight:750; letter-spacing:.13em; }
.brand-sub { color:var(--guide-muted); font:500 .75rem/1.5 ui-monospace, monospace; letter-spacing:.1em; margin:.65rem 0 0 46px; }

.section-label {
  color: var(--guide-gold); font: 650 .78rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .14em; text-transform: uppercase; margin: 1rem 0 .35rem;
}
.sidebar-copy { color:var(--guide-muted); font-size:.9rem; line-height:1.6; }
.sidebar-check { border-left:2px solid var(--guide-gold); padding:.2rem 0 .2rem .8rem; margin:.65rem 0; color:var(--guide-text); font-size:.9rem; line-height:1.55; }

.guide-topline {
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:.72rem 0 .9rem; border-bottom:1px solid var(--guide-line);
  color:var(--guide-muted); font:600 .78rem/1.4 ui-monospace, monospace; letter-spacing:.09em;
}
.guide-status { color:var(--guide-green); }
.guide-status::before { content:""; display:inline-block; width:7px; height:7px; margin-right:.5rem; border-radius:50%; background:var(--guide-green); box-shadow:0 0 12px rgba(111,220,155,.55); }

.guide-hero { display:grid; grid-template-columns:1.2fr .8fr; gap:1.5rem; padding:2.1rem 0 1.4rem; }
.guide-kicker { color:var(--guide-gold); font:650 .8rem/1.4 ui-monospace, monospace; letter-spacing:.14em; text-transform:uppercase; }
.guide-title { margin:.5rem 0 .75rem; color:var(--guide-text); font-size:clamp(2.4rem,5vw,5.2rem); line-height:.89; letter-spacing:-.055em; font-weight:780; }
.guide-title span { color:var(--guide-gold); }
.guide-lead { max-width:780px; margin:0; color:#c9c5bb; font-size:1.05rem; line-height:1.7; }
.guide-definition { border:1px solid var(--guide-line); background:rgba(5,9,14,.87); padding:1.2rem 1.25rem; align-self:end; }
.guide-definition strong { display:block; margin-bottom:.5rem; color:var(--guide-gold); font:650 .76rem/1.4 ui-monospace, monospace; letter-spacing:.12em; }
.guide-definition p { margin:0; color:var(--guide-muted); font-size:.98rem; line-height:1.65; }

.chip-row { display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0 1.8rem; }
.chip { padding:.42rem .62rem; border:1px solid var(--guide-line); background:rgba(8,15,23,.75); color:#cbc7bd; font:600 .76rem/1 ui-monospace, monospace; letter-spacing:.05em; }

.guide-section { margin:2.4rem 0 1rem; }
.guide-heading { margin:.25rem 0 .65rem; color:var(--guide-text); font-size:clamp(1.55rem,2.5vw,2.35rem); letter-spacing:-.025em; }
.guide-intro { max-width:920px; margin:0 0 1.2rem; color:var(--guide-muted); font-size:1rem; line-height:1.7; }

.start-grid { display:grid; grid-template-columns:repeat(5,1fr); border:1px solid var(--guide-line); background:rgba(5,9,14,.8); }
.start-step { min-height:144px; padding:1rem; border-right:1px solid var(--guide-line); }
.start-step:last-child { border-right:0; }
.step-index { color:var(--guide-gold); font:650 .8rem/1 ui-monospace, monospace; }
.step-title { margin:.7rem 0 .35rem; color:var(--guide-text); font-size:.98rem; font-weight:720; }
.step-copy { color:var(--guide-muted); font-size:.88rem; line-height:1.55; }

.callout {
  display:grid; grid-template-columns:auto 1fr; gap:1rem; align-items:start;
  margin:1.1rem 0; padding:1.05rem 1.1rem; border:1px solid var(--guide-line);
  border-left:3px solid var(--guide-gold); background:rgba(8,15,23,.72);
}
.callout-key { color:var(--guide-gold); font:700 .78rem/1.4 ui-monospace, monospace; letter-spacing:.08em; }
.callout-copy { color:#c8c4ba; font-size:.96rem; line-height:1.6; }

.arch-flow { display:grid; grid-template-columns:1fr auto 1fr auto 1fr auto 1fr; align-items:stretch; gap:.6rem; }
.arch-node { padding:1.05rem; border:1px solid var(--guide-line); background:linear-gradient(160deg,rgba(8,15,23,.95),rgba(3,6,10,.95)); }
.arch-index { color:var(--guide-gold); font:650 .73rem/1.3 ui-monospace, monospace; letter-spacing:.09em; }
.arch-title { margin:.65rem 0 .4rem; color:var(--guide-text); font-size:1rem; font-weight:720; }
.arch-copy { color:var(--guide-muted); font-size:.88rem; line-height:1.5; }
.arch-arrow { display:grid; place-items:center; color:var(--guide-gold); font-size:1.3rem; }
.return-path { margin-top:.7rem; padding:.7rem 1rem; border:1px dashed var(--guide-line-bright); color:var(--guide-muted); text-align:center; font:600 .78rem/1.5 ui-monospace, monospace; letter-spacing:.05em; }

.decision-rule { padding:1rem 1.2rem; border:1px solid var(--guide-line); background:#03070b; overflow-x:auto; color:#e6e2d9; font:650 .92rem/1.7 ui-monospace, monospace; }
.decision-rule .good { color:var(--guide-green); }
.decision-rule .gold { color:var(--guide-gold); }
.decision-rule .purple { color:var(--guide-purple); }

.guide-table { width:100%; border-collapse:collapse; border:1px solid var(--guide-line); background:rgba(5,9,14,.84); }
.guide-table th { padding:.85rem .9rem; border-bottom:1px solid var(--guide-line-bright); color:var(--guide-gold); text-align:left; font:650 .76rem/1.4 ui-monospace, monospace; letter-spacing:.08em; text-transform:uppercase; }
.guide-table td { padding:.9rem; border-bottom:1px solid var(--guide-line); color:#cbc7bd; font-size:.94rem; line-height:1.55; vertical-align:top; }
.guide-table tr:last-child td { border-bottom:0; }
.guide-table td:first-child { color:var(--guide-text); font-weight:700; white-space:nowrap; }
.value { color:var(--guide-green); font:650 .84rem ui-monospace, monospace; white-space:nowrap; }

.mode-grid, .read-grid, .state-grid { display:grid; gap:.8rem; }
.mode-grid { grid-template-columns:repeat(2,1fr); }
.read-grid { grid-template-columns:repeat(3,1fr); }
.state-grid { grid-template-columns:repeat(4,1fr); }
.info-card { padding:1rem 1.05rem; border:1px solid var(--guide-line); background:rgba(5,9,14,.82); }
.info-card.accent { border-top:2px solid var(--guide-gold); }
.info-card.green { border-top:2px solid var(--guide-green); }
.card-kicker { color:var(--guide-gold); font:650 .74rem/1.3 ui-monospace, monospace; letter-spacing:.08em; text-transform:uppercase; }
.card-title { margin:.55rem 0 .35rem; color:var(--guide-text); font-size:1rem; font-weight:720; }
.card-copy { color:var(--guide-muted); font-size:.92rem; line-height:1.58; }
.state-name { color:var(--guide-text); font:700 .82rem/1.3 ui-monospace, monospace; letter-spacing:.05em; }
.state-copy { margin-top:.4rem; color:var(--guide-muted); font-size:.88rem; line-height:1.48; }

.limit-note { padding:1.05rem 1.15rem; border:1px solid #59452a; background:rgba(89,69,42,.14); color:#d5c8b3; font-size:.96rem; line-height:1.65; }
.port-list { display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; }
.port { padding:.9rem 1rem; border:1px solid var(--guide-line); background:rgba(5,9,14,.82); }
.port strong { display:block; color:var(--guide-gold); font:700 1rem/1.2 ui-monospace, monospace; }
.port span { color:var(--guide-muted); font-size:.9rem; }

[data-testid="stExpander"] { border:1px solid var(--guide-line); border-radius:2px; background:rgba(5,9,14,.78); }
[data-testid="stExpander"] summary p { color:var(--guide-text); font-size:.95rem; font-weight:650; }
[data-testid="stCode"] { border:1px solid var(--guide-line); border-radius:2px; }

@media (max-width: 1050px) {
  .guide-hero, .mode-grid { grid-template-columns:1fr; }
  .start-grid { grid-template-columns:repeat(2,1fr); }
  .start-step { border-bottom:1px solid var(--guide-line); }
  .read-grid, .state-grid { grid-template-columns:repeat(2,1fr); }
  .arch-flow { grid-template-columns:1fr; }
  .arch-arrow { transform:rotate(90deg); min-height:28px; }
}
@media (max-width: 680px) {
  .block-container { padding:1rem 1rem 3rem; }
  .start-grid, .read-grid, .state-grid, .port-list { grid-template-columns:1fr; }
  .start-step { border-right:0; }
  .guide-topline { align-items:flex-start; flex-direction:column; }
  .guide-title { font-size:2.65rem; }
  .guide-table { display:block; overflow-x:auto; }
}
</style>
"""

st.markdown(GUIDE_CSS, unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        """
        <div class="brand-lockup">
          <span class="brand-mark"><span>✦</span></span>
          <span class="brand-name">AEROLAND</span>
          <div class="brand-sub">PROJECT GUIDE / V1.0</div>
        </div>
        <div class="section-label">Navigation</div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("streamlit_app.py", label="Mission control")
    st.page_link("pages/Project_Guide.py", label="Project guide")
    st.markdown("---")
    st.markdown(
        """
        <div class="section-label">First mission</div>
        <div class="sidebar-check"><strong>1.</strong> Open Mission control</div>
        <div class="sidebar-check"><strong>2.</strong> Keep Nominal mission selected</div>
        <div class="sidebar-check"><strong>3.</strong> Choose the runner</div>
        <div class="sidebar-check"><strong>4.</strong> Press Run mission</div>
        <div class="sidebar-check"><strong>5.</strong> Review the data below the viewer</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        """
        <div class="section-label">Recommended values</div>
        <div class="sidebar-copy">
          Altitude: <strong>2.50 m</strong><br>
          Wind: <strong>0.00 m/s</strong><br>
          Confidence: <strong>0.60</strong><br>
          Radial sigma: <strong>0.12 m</strong><br>
          Seed: <strong>7</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="guide-topline">
      <span>AEROLAND / DOCUMENTATION / PROJECT GUIDE</span>
      <span class="guide-status">OPERATOR REFERENCE</span>
    </div>
    <div class="guide-hero">
      <div>
        <div class="guide-kicker">Autonomy system overview</div>
        <h1 class="guide-title">UNDERSTAND<br><span>THE MISSION.</span></h1>
        <p class="guide-lead">AeroLand is a ROS 2 and PX4 simulation for autonomous aerial inspection and uncertainty-aware precision landing. This page explains what the system does, how to run it, and how to interpret every major result.</p>
      </div>
      <div class="guide-definition">
        <strong>THE CORE IDEA</strong>
        <p>The drone does not descend simply because it sees the landing marker. It descends only when the marker is detected, the landing confidence is high enough, and the estimated position uncertainty is below the selected safety limit.</p>
      </div>
    </div>
    <div class="chip-row">
      <span class="chip">ROS 2 HUMBLE</span>
      <span class="chip">PX4 SITL</span>
      <span class="chip">GAZEBO</span>
      <span class="chip">ARUCO LANDING</span>
      <span class="chip">10 HZ TELEMETRY</span>
      <span class="chip">FASTAPI + STREAMLIT</span>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">01 / Start here</div>
      <h2 class="guide-heading">Run your first mission in five steps</h2>
      <p class="guide-intro">For the first run, leave the validated default values unchanged. Once that mission completes, change one setting at a time so its effect is easy to understand.</p>
    </div>
    <div class="start-grid">
      <div class="start-step"><div class="step-index">01</div><div class="step-title">Open Mission control</div><div class="step-copy">Use the navigation on the left to return to the operating console.</div></div>
      <div class="start-step"><div class="step-index">02</div><div class="step-title">Choose a runner</div><div class="step-copy">Use Browser digital twin for a quick demo or Local mission backend for PX4 and Gazebo.</div></div>
      <div class="start-step"><div class="step-index">03</div><div class="step-title">Keep Nominal mission</div><div class="step-copy">The default preset is the clearest and safest place to begin.</div></div>
      <div class="start-step"><div class="step-index">04</div><div class="step-title">Press Run mission</div><div class="step-copy">Wait while the drone takes off, inspects, finds the marker, and attempts to land.</div></div>
      <div class="start-step"><div class="step-index">05</div><div class="step-title">Review the evidence</div><div class="step-copy">Replay the flight, inspect the safety charts, and download the mission files.</div></div>
    </div>
    <div class="callout">
      <div class="callout-key">FIRST-RUN RULE</div>
      <div class="callout-copy">If you select <strong>Local mission backend</strong>, wait for the green PX4/Gazebo-ready message before pressing Run mission. If it says the backend is offline, the local API terminal must be started first.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">02 / System architecture</div>
      <h2 class="guide-heading">How the parts work together</h2>
      <p class="guide-intro">The website is the operator interface. It sends one validated mission request to the API, which coordinates the autonomy software and simulator. Telemetry then returns to the website for visualization and analysis.</p>
    </div>
    <div class="arch-flow">
      <div class="arch-node"><div class="arch-index">01 / INTERFACE</div><div class="arch-title">Streamlit website</div><div class="arch-copy">Collects mission settings, shows the live twin, and presents results.</div></div>
      <div class="arch-arrow">→</div>
      <div class="arch-node"><div class="arch-index">02 / ORCHESTRATE</div><div class="arch-title">FastAPI backend</div><div class="arch-copy">Validates the request and manages one simulator mission at a time.</div></div>
      <div class="arch-arrow">→</div>
      <div class="arch-node"><div class="arch-index">03 / AUTONOMY</div><div class="arch-title">ROS 2 nodes</div><div class="arch-copy">Run inspection, marker perception, uncertainty estimation, and landing logic.</div></div>
      <div class="arch-arrow">→</div>
      <div class="arch-node"><div class="arch-index">04 / PHYSICS</div><div class="arch-title">PX4 + Gazebo</div><div class="arch-copy">Simulate the flight controller, X500 vehicle, sensors, wind force, and world.</div></div>
    </div>
    <div class="return-path">TELEMETRY RETURN PATH ← state · pose · altitude · confidence · sigma · descent approval</div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">03 / Mission sequence</div>
      <h2 class="guide-heading">What happens after you press Run mission</h2>
      <p class="guide-intro">The controller follows a state machine. It must finish each phase—or deliberately recover—before it can move to the next phase.</p>
    </div>
    <div class="state-grid">
      <div class="info-card"><div class="state-name">WAITING</div><div class="state-copy">The system is idle and waiting for a valid mission start.</div></div>
      <div class="info-card"><div class="state-name">PRESTREAM</div><div class="state-copy">Initial position targets are sent before PX4 accepts offboard control.</div></div>
      <div class="info-card"><div class="state-name">ACTIVATE</div><div class="state-copy">PX4 enters the required control mode and prepares the vehicle.</div></div>
      <div class="info-card"><div class="state-name">TAKEOFF</div><div class="state-copy">The X500 climbs to the chosen cruise altitude.</div></div>
      <div class="info-card"><div class="state-name">INSPECTION</div><div class="state-copy">The drone follows the planned inspection route.</div></div>
      <div class="info-card"><div class="state-name">SEARCH</div><div class="state-copy">The downward camera looks for the ArUco landing marker.</div></div>
      <div class="info-card"><div class="state-name">ALIGN</div><div class="state-copy">The controller centers the vehicle over the marker.</div></div>
      <div class="info-card"><div class="state-name">DESCEND</div><div class="state-copy">Altitude decreases only while all safety conditions are satisfied.</div></div>
      <div class="info-card"><div class="state-name">RECOVER</div><div class="state-copy">The drone holds or repositions when confidence or uncertainty is unsafe.</div></div>
      <div class="info-card"><div class="state-name">LANDING</div><div class="state-copy">PX4 receives the final landing handoff near the target.</div></div>
      <div class="info-card green"><div class="state-name">COMPLETE</div><div class="state-copy">The mission ended successfully and results are available.</div></div>
      <div class="info-card accent"><div class="state-name">ABORTED / FAILED</div><div class="state-copy">The system stopped safely or encountered a simulator/software error.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">04 / Safety logic</div>
      <h2 class="guide-heading">Why the descent gate opens or closes</h2>
      <p class="guide-intro">AeroLand treats landing as an evidence-based decision. The selected thresholds become explicit rules rather than hidden tuning values.</p>
    </div>
    <div class="decision-rule">
      <span class="good">DESCENT APPROVED</span> = MARKER DETECTED<br>
      &nbsp;&nbsp;AND CONFIDENCE <span class="gold">≥ MINIMUM CONFIDENCE</span><br>
      &nbsp;&nbsp;AND RADIAL SIGMA <span class="purple">≤ MAXIMUM RADIAL SIGMA</span>
    </div>
    <div class="callout">
      <div class="callout-key">PLAIN LANGUAGE</div>
      <div class="callout-copy"><strong>Confidence</strong> describes how trustworthy the landing estimate is; higher is better. <strong>Radial sigma</strong> describes the estimated horizontal position uncertainty in meters; lower is better. If either test fails, descent pauses instead of forcing a risky landing.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">05 / Controls</div>
      <h2 class="guide-heading">What each setting changes</h2>
    </div>
    <table class="guide-table">
      <thead><tr><th>Control</th><th>Meaning</th><th>Recommended first run</th><th>What happens when increased</th></tr></thead>
      <tbody>
        <tr><td>Mission preset</td><td>Loads a coordinated group of starting values.</td><td><span class="value">Nominal mission</span></td><td>Depends on the selected preset.</td></tr>
        <tr><td>Cruise altitude</td><td>Target altitude during the inspection route.</td><td><span class="value">2.50 m</span></td><td>The vehicle climbs higher and the route may take longer.</td></tr>
        <tr><td>Wind disturbance</td><td>Requested environmental disturbance from 0.00 to 8.00 m/s. Live mode converts it into a horizontal Gazebo force.</td><td><span class="value">0.00 m/s</span></td><td>Tracking and landing become more difficult.</td></tr>
        <tr><td>Minimum confidence</td><td>Lowest acceptable landing-confidence score.</td><td><span class="value">0.60</span></td><td>The descent rule becomes more conservative.</td></tr>
        <tr><td>Maximum radial sigma</td><td>Largest acceptable horizontal uncertainty.</td><td><span class="value">0.12 m</span></td><td>The descent rule becomes less conservative because more uncertainty is allowed.</td></tr>
        <tr><td>Simulation seed</td><td>Creates a repeatable scenario. In live wind runs, it selects the disturbance direction.</td><td><span class="value">7</span></td><td>The number itself is not stronger or weaker; it selects a different repeatable case.</td></tr>
      </tbody>
    </table>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">06 / Operating modes</div>
      <h2 class="guide-heading">Browser demonstration versus live simulation</h2>
    </div>
    <div class="mode-grid">
      <div class="info-card accent">
        <div class="card-kicker">Fast learning mode</div>
        <div class="card-title">Browser digital twin</div>
        <div class="card-copy">Generates deterministic synthetic telemetry inside the web application. Use it to learn the controls, charts, thresholds, and mission logic without starting PX4 or Gazebo. It is not a physical-flight result.</div>
      </div>
      <div class="info-card green">
        <div class="card-kicker">Local integration mode</div>
        <div class="card-title">Local mission backend</div>
        <div class="card-copy">Runs the ROS 2 mission against PX4 SITL and Gazebo on the local computer. The desktop Gazebo window is the authoritative physics simulation; the embedded X500 is a synchronized browser twin driven by live pose telemetry.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">07 / Reading the dashboard</div>
      <h2 class="guide-heading">Where to find the important evidence</h2>
    </div>
    <div class="read-grid">
      <div class="info-card"><div class="card-title">Live Gazebo twin</div><div class="card-copy">Shows the X500 pose during a local mission. Drag to orbit and scroll to zoom.</div></div>
      <div class="info-card"><div class="card-title">Mission replay</div><div class="card-copy">Move the timeline to inspect the vehicle state, sensor lock, confidence, sigma, and descent decision at any moment.</div></div>
      <div class="info-card"><div class="card-title">Altitude profile</div><div class="card-copy">Confirms takeoff, cruise, descent holds, and landing behavior over time.</div></div>
      <div class="info-card"><div class="card-title">Confidence chart</div><div class="card-copy">Compares landing confidence with the minimum threshold. Values below the line block descent.</div></div>
      <div class="info-card"><div class="card-title">Uncertainty chart</div><div class="card-copy">Compares radial sigma with the maximum limit. Values above the line block descent.</div></div>
      <div class="info-card"><div class="card-title">State timeline</div><div class="card-copy">Shows when the mission advanced, held, recovered, completed, or aborted.</div></div>
      <div class="info-card"><div class="card-title">Results tab</div><div class="card-copy">Provides the verdict, plain-language interpretation, mission report, and event record.</div></div>
      <div class="info-card"><div class="card-title">System tab</div><div class="card-copy">Explains the control architecture and separates demonstrated results from verified live benchmarks.</div></div>
      <div class="info-card"><div class="card-title">Downloads</div><div class="card-copy">Exports a complete ZIP bundle, telemetry CSV, technical report PNG, or summary text file.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">08 / Local services</div>
      <h2 class="guide-heading">What must be running</h2>
      <p class="guide-intro">A local Gazebo mission uses three local services. The website may be open even when the mission API is not running, which is why the interface can report that the backend is offline.</p>
    </div>
    <div class="port-list">
      <div class="port"><strong>8501</strong><span>Streamlit website</span></div>
      <div class="port"><strong>8000</strong><span>Mission API</span></div>
      <div class="port"><strong>9002</strong><span>Gazebo pose bridge</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Operator startup commands — backend terminal"):
    st.caption("Run these commands in Ubuntu/WSL, not Windows PowerShell. Leave this terminal running.")
    st.code(
        """sudo mkdir -p /mnt/shared_memory
mountpoint -q /mnt/shared_memory || sudo mount -t tmpfs tmpfs /mnt/shared_memory

cd /home/shivali/aeroland_ws/web
source /opt/ros/humble/setup.bash
source /home/shivali/aeroland_ws/install/setup.bash
source .venv/bin/activate

unset HEADLESS
export AEROLAND_RUNNER_MODE=gazebo
export AEROLAND_WORKSPACE=/home/shivali/aeroland_ws
export PX4_AUTOPILOT_DIR=/home/shivali/PX4-Autopilot
export AEROLAND_START_XRCE=1
export AEROLAND_START_GCS_HEARTBEAT=1
export AEROLAND_START_GZWEB=1
export AEROLAND_GAZEBO_HEADLESS=0
export AEROLAND_MISSION_TIMEOUT=300

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000""",
        language="bash",
    )

with st.expander("Operator startup commands — website terminal"):
    st.caption("Open a second Ubuntu/WSL terminal and leave it running.")
    st.code(
        """cd /home/shivali/aeroland_ws/web
source .venv/bin/activate

WSL_IP=$(hostname -I | awk '{print $1}')
export AEROLAND_SIM_API_URL=http://127.0.0.1:8000
export AEROLAND_GAZEBO_VIEW_URL="http://127.0.0.1:8000/gazebo-view/?ws=ws://${WSL_IP}:9002&v=project-guide"

python -m streamlit run streamlit_app.py""",
        language="bash",
    )


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">09 / Troubleshooting</div>
      <h2 class="guide-heading">What the common messages mean</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Mission backend offline"):
    st.write("The website is running, but it cannot reach the API on port 8000. Start the backend terminal, keep it open, then refresh the page.")

with st.expander("Waiting for Gazebo"):
    st.write("The embedded twin intentionally waits until a new local mission begins publishing simulator telemetry. Select Local mission backend and press Run mission.")

with st.expander("Gazebo view unavailable or disconnected"):
    st.write("The optional browser bridge stopped, but the physical mission may still be running in the desktop Gazebo window. The desktop simulator remains authoritative. Inspect the run's gzweb_bridge.log file if the problem repeats.")

with st.expander("The embedded drone does not appear"):
    st.write("Wait for the local mission to begin, then press Ctrl+Shift+R once. Confirm the embedded label reports GRAPHITE X500 READY and that port 9002 is reachable from Windows.")

with st.expander("Mission exceeded the safety timeout"):
    st.write("The mission did not reach COMPLETE within the configured time. Inspect the newest folder under ~/.aeroland/runs/—especially px4_gazebo.log, aeroland.log, and the telemetry directory.")


st.markdown(
    """
    <div class="guide-section">
      <div class="section-label">10 / Scope and limitations</div>
      <h2 class="guide-heading">What the project proves—and what it does not</h2>
    </div>
    <div class="limit-note">
      AeroLand demonstrates a complete local autonomy-integration workflow: mission configuration, PX4/Gazebo simulation, ROS 2 state control, visual-marker landing logic, uncertainty gating, telemetry analysis, and operator reporting. It does <strong>not</strong> claim real-aircraft certification. The live wind setting is a wind-equivalent horizontal force, not a full computational-fluid-dynamics model, and the embedded X500 is a synchronized pose twin rather than a second physics simulator.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
st.page_link("streamlit_app.py", label="Open Mission control")
