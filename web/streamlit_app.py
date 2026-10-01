"""AeroLand technical mission-control web experience."""

from __future__ import annotations

import html
import os
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from aeroland_web.api_client import MissionAPIError, backend_health, run_remote_mission
from aeroland_web.browser_twin import browser_twin_html
from aeroland_web.charts import (
    altitude_chart,
    confidence_chart,
    error_chart,
    mission_view,
    sensor_reticle,
    sigma_chart,
    state_chart,
)
from aeroland_web.reporting import event_log, render_report_png, result_bundle, summary_text
from aeroland_web.simulation import MissionConfig, MissionResult, run_mission


st.set_page_config(
    page_title="AeroLand | Mission Operations",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
:root {
  --al-bg: #020406;
  --al-panel: #070b10;
  --al-panel-2: #0b1118;
  --al-line: #2c2e30;
  --al-line-bright: #494a47;
  --al-text: #f2f0ea;
  --al-muted: #a8a8a3;
  --al-cyan: #d6a34a;
  --al-blue: #f2f0ea;
  --al-purple: #b9a4d8;
  --al-amber: #d6a34a;
  --al-green: #67d391;
  --al-red: #ff6b78;
}

html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
  color: var(--al-text);
  background-color: #020406;
  background-image:
    radial-gradient(circle, rgba(240, 250, 255, .48) 0 .65px, transparent .85px),
    radial-gradient(circle, rgba(214, 163, 74, .30) 0 .55px, transparent .8px),
    radial-gradient(circle, rgba(168, 137, 255, .28) 0 .65px, transparent .9px),
    radial-gradient(ellipse at 78% -15%, rgba(36, 88, 128, .22), transparent 38%),
    radial-gradient(ellipse at 15% 105%, rgba(54, 31, 100, .14), transparent 38%),
    linear-gradient(180deg, #03070b 0%, #020406 48%, #000 100%);
  background-size: 83px 83px, 137px 137px, 211px 211px, auto, auto, auto;
  background-position: 7px 13px, 43px 71px, 111px 29px, center, center, center;
  background-attachment: fixed;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { max-width: 1580px; padding: 1.1rem 2.2rem 3.5rem; }

[data-testid="stSidebar"] {
  width: 346px !important;
  background: linear-gradient(180deg, rgba(4, 9, 14, .985) 0%, rgba(0, 2, 5, .99) 100%);
  border-right: 1px solid var(--al-line);
}
[data-testid="stSidebar"] > div:first-child { width: 346px !important; }
[data-testid="stSidebar"] .block-container { padding: 1.35rem 1.4rem 2rem; }
[data-testid="stSidebar"] hr { border-color: var(--al-line); margin: 1.2rem 0; }
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stPageLink"] { margin: .28rem 0; }
[data-testid="stPageLink"] a,
a[data-testid="stPageLink-NavLink"] {
  min-height: 2.45rem; padding: .6rem .72rem; border: 1px solid var(--al-line);
  border-radius: 2px; background: rgba(8,15,23,.72); color: var(--al-text) !important;
  font: 650 .72rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .08em; text-transform: uppercase; text-decoration: none;
}
[data-testid="stPageLink"] a:hover,
a[data-testid="stPageLink-NavLink"]:hover {
  border-color: var(--al-cyan); background: rgba(214,163,74,.08);
}

.brand-lockup { padding: .15rem 0 1.35rem; }
.brand-mark {
  display: inline-grid; place-items: center; width: 34px; height: 34px;
  margin-right: 10px; border: 1px solid var(--al-cyan); color: var(--al-cyan);
  font: 700 18px/1 ui-monospace, monospace; transform: rotate(45deg);
  box-shadow: 0 0 26px rgba(214,163,74,.14); vertical-align: middle;
}
.brand-mark > span { transform: rotate(-45deg); }
.brand-name { display:inline-block; vertical-align:middle; font-size: 1.02rem; font-weight: 750; letter-spacing: .13em; }
.brand-sub { color: var(--al-muted); font: 500 .64rem/1.5 ui-monospace, monospace; letter-spacing: .13em; margin: .65rem 0 0 46px; }

.section-label {
  color: var(--al-cyan); font: 650 .64rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .16em; text-transform: uppercase; margin: .55rem 0 .2rem;
}
.sidebar-copy { color: var(--al-muted); font-size: .75rem; line-height: 1.55; margin-bottom: .9rem; }
.safety-envelope {
  border: 1px solid var(--al-line); background: rgba(4,9,14,.84);
  padding: .85rem .9rem; margin-top: 1rem;
}
.safety-row { display:flex; align-items:center; justify-content:space-between; padding:.30rem 0; border-bottom:1px solid rgba(27,53,71,.6); }
.safety-row:last-child { border-bottom:0; }
.safety-k { color:var(--al-muted); font: .63rem ui-monospace, monospace; letter-spacing:.08em; }
.safety-v { color:var(--al-text); font: .68rem ui-monospace, monospace; }

label, [data-testid="stWidgetLabel"] p {
  color: #b0aca3 !important; font-size: .72rem !important; font-weight: 600 !important;
  letter-spacing: .035em;
}
[data-baseweb="select"] > div, [data-testid="stNumberInput"] input {
  background: #050b11 !important; border-color: var(--al-line) !important;
}
[data-testid="stSlider"] [role="slider"] { background: var(--al-cyan); border-color: #f2f0ea; box-shadow:0 0 14px rgba(214,163,74,.20); }

.stButton > button, .stDownloadButton > button, .stLinkButton > a {
  min-height: 2.65rem; border-radius: 2px; border: 1px solid var(--al-cyan) !important;
  background: rgba(214, 163, 74, .06) !important; color: #f2f0ea !important;
  font: 700 .68rem/1 ui-monospace, SFMono-Regular, Menlo, monospace !important;
  letter-spacing: .10em; text-transform: uppercase; transition: all .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
  background: rgba(214,163,74,.14) !important; box-shadow: 0 0 26px rgba(214,163,74,.11);
}
[data-testid="stSidebar"] .stButton > button { width:100%; background: var(--al-cyan) !important; color:#00060a !important; }
[data-testid="stSidebar"] .stButton > button:disabled { background:#1a1917 !important; color:#77736b !important; border-color:#37342f !important; }

.ops-topbar {
  display:flex; align-items:center; justify-content:space-between; gap:1.5rem;
  min-height:44px; border-bottom:1px solid var(--al-line); padding:0 0 .85rem; margin-bottom:1.65rem;
}
.ops-path { color:var(--al-muted); font:.65rem ui-monospace,monospace; letter-spacing:.11em; }
.ops-path strong { color:var(--al-text); font-weight:600; }
.sys-array { display:flex; align-items:center; gap:1.15rem; flex-wrap:wrap; justify-content:flex-end; }
.sys-item { color:var(--al-muted); font:.61rem ui-monospace,monospace; letter-spacing:.08em; white-space:nowrap; }
.sys-item b { color:var(--al-text); font-weight:600; }
.status-dot { display:inline-block; width:6px; height:6px; border-radius:50%; margin-right:6px; background:var(--al-green); box-shadow:0 0 10px var(--al-green); }
.status-dot.amber { background:var(--al-amber); box-shadow:0 0 10px var(--al-amber); }

.hero-grid { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(340px,.6fr); gap:2.4rem; align-items:end; margin-bottom:1.3rem; }
.hero-kicker { color:var(--al-cyan); font:.66rem ui-monospace,monospace; letter-spacing:.17em; text-transform:uppercase; margin-bottom:.7rem; }
.hero-title { margin:0; font-size:clamp(2.1rem,4vw,4.45rem); line-height:.93; letter-spacing:-.055em; font-weight:760; color:#f7f4ed; }
.hero-title span { color:#8c8982; font-weight:500; }
.hero-copy { margin:.95rem 0 0; max-width:770px; color:#a29d94; font-size:.92rem; line-height:1.65; }
.hero-note {
  border-left:2px solid var(--al-amber); padding:.15rem 0 .15rem 1rem;
  color:#aaa59b; font:.69rem/1.65 ui-monospace,monospace;
}
.hero-note strong { display:block; color:var(--al-amber); font-size:.65rem; letter-spacing:.10em; margin-bottom:.25rem; }

.status-ribbon {
  display:grid; grid-template-columns:repeat(5,1fr); border:1px solid var(--al-line);
  background:rgba(2,7,11,.88); margin:.55rem 0 1.05rem;
}
.ribbon-cell { padding:.72rem .85rem; border-right:1px solid var(--al-line); min-width:0; }
.ribbon-cell:last-child { border-right:0; }
.ribbon-k { display:block; color:#858078; font:.57rem ui-monospace,monospace; letter-spacing:.12em; text-transform:uppercase; }
.ribbon-v { display:block; margin-top:.25rem; color:#ece8df; font:.72rem ui-monospace,monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ribbon-v.good { color:var(--al-green); } .ribbon-v.warn { color:var(--al-amber); } .ribbon-v.bad { color:var(--al-red); }

.metric-card {
  min-height:112px; border:1px solid var(--al-line); background:linear-gradient(145deg,rgba(7,14,21,.94),rgba(1,5,8,.88));
  padding:1rem 1.05rem; position:relative; overflow:hidden;
}
.metric-card::after { content:""; position:absolute; top:0; right:0; width:34px; height:1px; background:var(--metric-color,var(--al-cyan)); }
.metric-k { color:#938e85; font:.58rem ui-monospace,monospace; letter-spacing:.12em; text-transform:uppercase; }
.metric-v { color:#f5f1e8; font:650 1.72rem/1.1 ui-monospace,SFMono-Regular,Menlo,monospace; margin:.55rem 0 .42rem; letter-spacing:-.045em; }
.metric-foot { color:#858078; font:.60rem ui-monospace,monospace; letter-spacing:.035em; }
.metric-foot strong { color:var(--metric-color,var(--al-cyan)); font-weight:600; }

.panel-shell { border:1px solid var(--al-line); background:rgba(2,7,11,.84); padding:.35rem .7rem .55rem; }
.panel-heading { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--al-line); padding:.62rem .25rem .58rem; margin:0 .15rem .1rem; }
.panel-title { color:#c7c2b8; font:.63rem ui-monospace,monospace; letter-spacing:.13em; text-transform:uppercase; }
.panel-meta { color:#7f7a72; font:.57rem ui-monospace,monospace; letter-spacing:.08em; }
.readout-grid { display:grid; grid-template-columns:repeat(5,1fr); border:1px solid var(--al-line); margin:.75rem 0 1rem; }
.readout { padding:.72rem .78rem; border-right:1px solid var(--al-line); }
.readout:last-child { border-right:0; }
.readout-k { color:#858078; font:.56rem ui-monospace,monospace; letter-spacing:.12em; }
.readout-v { color:#f0ece3; font:700 .91rem ui-monospace,monospace; margin-top:.26rem; }
.readout-v.good { color:var(--al-green); } .readout-v.bad { color:var(--al-red); } .readout-v.warn { color:var(--al-amber); }

.stTabs [data-baseweb="tab-list"] { gap:0; border-bottom:1px solid var(--al-line); margin:1.35rem 0 .75rem; }
.stTabs [data-baseweb="tab"] {
  height:2.9rem; padding:0 1.3rem; color:#8e8981; background:transparent; border-radius:0;
  font:650 .65rem ui-monospace,monospace; letter-spacing:.12em;
}
.stTabs [aria-selected="true"] { color:var(--al-cyan) !important; border-bottom:2px solid var(--al-cyan); }
.stTabs [data-baseweb="tab-highlight"] { background:var(--al-cyan); }

.verdict {
  border:1px solid var(--al-line); border-left:3px solid var(--verdict-color,var(--al-cyan));
  padding:1.15rem 1.25rem; background:rgba(4,10,15,.9); margin:.5rem 0 1rem;
  display:flex; justify-content:space-between; gap:2rem; align-items:center;
}
.verdict-k { color:#928e85; font:.58rem ui-monospace,monospace; letter-spacing:.13em; }
.verdict-v { color:var(--verdict-color,var(--al-cyan)); font:750 1.25rem ui-monospace,monospace; letter-spacing:.08em; margin-top:.25rem; }
.verdict-copy { color:#a6a198; font-size:.78rem; max-width:740px; line-height:1.55; }

.architecture { display:grid; grid-template-columns:repeat(5,1fr); gap:18px; margin:1.1rem 0 1.7rem; align-items:stretch; }
.arch-node { position:relative; border:1px solid var(--al-line); background:rgba(4,10,15,.9); padding:1rem; min-height:112px; }
.arch-node:not(:last-child)::after { content:"→"; position:absolute; right:-15px; top:43%; color:var(--al-cyan); font:700 14px ui-monospace,monospace; }
.arch-index { color:var(--al-cyan); font:.56rem ui-monospace,monospace; letter-spacing:.12em; }
.arch-title { color:#e6e1d8; font:700 .73rem ui-monospace,monospace; letter-spacing:.06em; margin:.45rem 0; }
.arch-copy { color:#938f87; font-size:.66rem; line-height:1.45; }
.disclosure { border:1px solid #73582b; background:rgba(79,56,20,.16); color:#c9b584; padding:.9rem 1rem; font:.68rem/1.6 ui-monospace,monospace; }
.disclosure strong { color:var(--al-amber); }

.preset-note { border-left:2px solid var(--al-amber); padding:.35rem .65rem; margin:.3rem 0 .85rem; color:#918d85; font:.62rem/1.5 ui-monospace,monospace; }
.interpretation { border:1px solid var(--al-line); background:rgba(2,7,11,.9); padding:.95rem 1.05rem; margin:.55rem 0 1rem; }
.interpretation strong { color:#e6e1d8; font:.67rem ui-monospace,monospace; letter-spacing:.08em; }
.interpretation p { color:#9e9a91; font-size:.74rem; line-height:1.6; margin:.45rem 0 0; }

[data-testid="stDataFrame"] { border:1px solid var(--al-line); }
[data-testid="stPlotlyChart"] { border:1px solid var(--al-line); background:rgba(1,5,8,.78); padding:.18rem; }
[data-testid="stExpander"] { border:1px solid var(--al-line); border-radius:0; background:rgba(2,7,11,.82); }
[data-testid="stProgressBar"] > div > div { background:var(--al-cyan); }
.stAlert { border-radius:0; border-left-width:2px; background:rgba(4,10,15,.94); }

@media (max-width: 1050px) {
  .hero-grid { grid-template-columns:1fr; gap:1rem; }
  .status-ribbon, .readout-grid { grid-template-columns:repeat(2,1fr); }
  .ribbon-cell, .readout { border-bottom:1px solid var(--al-line); }
  .architecture { grid-template-columns:1fr 1fr; }
  .arch-node::after { display:none; }
}
@media (max-width: 720px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .ops-topbar { align-items:flex-start; flex-direction:column; }
  .sys-array { justify-content:flex-start; }
  .hero-title { font-size:2.5rem; }
  .status-ribbon, .readout-grid, .architecture { grid-template-columns:1fr; }
  .ribbon-cell, .readout { border-right:0; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


MISSION_API_CONFIGURED = bool(os.getenv("AEROLAND_SIM_API_URL", "").strip())
MISSION_API_URL = os.getenv("AEROLAND_SIM_API_URL", "http://127.0.0.1:8000")
GAZEBO_VIEW_URL = os.getenv(
    "AEROLAND_GAZEBO_VIEW_URL",
    f"{MISSION_API_URL.rstrip('/')}/gazebo-view/",
)


@st.cache_data(ttl=3, show_spinner=False)
def _backend_health(base_url: str) -> dict:
    """Avoid repeated health requests during one Streamlit rerun cycle."""

    return backend_health(base_url)


PRESETS = {
    "Nominal mission": {
        "confidence_input": 0.60,
        "sigma_input": 0.12,
        "altitude_input": 2.50,
        "wind_input": 0.0,
    },
    "Crosswind evaluation": {
        "confidence_input": 0.60,
        "sigma_input": 0.12,
        "altitude_input": 2.50,
        "wind_input": 2.0,
    },
    "Conservative safety": {
        "confidence_input": 0.75,
        "sigma_input": 0.08,
        "altitude_input": 2.50,
        "wind_input": 1.0,
    },
    "Stress test": {
        "confidence_input": 0.80,
        "sigma_input": 0.07,
        "altitude_input": 3.00,
        "wind_input": 4.5,
    },
}

PRESET_DESCRIPTIONS = {
    "Nominal mission": "Recommended first run with the validated default safety envelope.",
    "Crosswind evaluation": "Adds moderate wind while retaining the default descent limits.",
    "Conservative safety": "Uses stricter confidence and uncertainty limits with light wind.",
    "Stress test": "Designed to exercise holds, recovery behavior, and possible mission abort.",
}


def _metric_card(label: str, value: str, footer: str, color: str = "#d6a34a") -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--metric-color:{color}">
          <div class="metric-k">{html.escape(label)}</div>
          <div class="metric-v">{html.escape(value)}</div>
          <div class="metric-foot">{footer}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _panel_heading(title: str, meta: str) -> None:
    st.markdown(
        f"""
        <div class="panel-heading">
          <span class="panel-title">{html.escape(title)}</span>
          <span class="panel-meta">{html.escape(meta)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_preset() -> None:
    """Load a scenario preset into the editable mission controls."""

    values = PRESETS[st.session_state.mission_preset]
    for key, value in values.items():
        st.session_state[key] = value


def _risk_label(config: MissionConfig) -> tuple[str, str]:
    """Return a simple scenario-complexity label for the status ribbon."""

    if (
        config.wind_speed_mps >= 4.0
        or config.confidence_threshold >= 0.80
        or config.sigma_threshold_m <= 0.07
    ):
        return "HIGH", "bad"
    if (
        config.wind_speed_mps >= 1.5
        or config.confidence_threshold >= 0.70
        or config.sigma_threshold_m <= 0.09
    ):
        return "ELEVATED", "warn"
    return "NOMINAL", "good"


def _interpretation(result: MissionResult) -> str:
    """Explain the mission outcome without requiring chart expertise."""

    metrics = result.metrics
    if metrics["mission_status"] != "COMPLETE":
        return (
            "The mission aborted because the selected environmental conditions and safety limits "
            "did not provide a sufficiently reliable descent window before timeout. The controller "
            "failed safely rather than forcing an uncertain landing."
        )
    approval = metrics["descent_approval_pct"]
    if approval >= 85.0:
        gate_text = "The descent gate remained open for most of the landing sequence."
    elif approval >= 55.0:
        gate_text = "The controller made frequent safety holds but still found enough valid windows to land."
    else:
        gate_text = "The safety envelope was restrictive, so descent progressed only through short approved windows."
    return (
        f"{gate_text} AeroLand recorded {metrics['uncertainty_pause_events']} uncertainty pauses, "
        f"{metrics['recovery_events']} recovery events, and a synthetic final target offset of "
        f"{100 * metrics['final_horizontal_error_m']:.1f} cm."
    )


def _initialize() -> None:
    if "mission_result" not in st.session_state:
        st.session_state.mission_result = run_mission(MissionConfig())
    if "run_number" not in st.session_state:
        st.session_state.run_number = 1
    if "mission_preset" not in st.session_state:
        st.session_state.mission_preset = "Nominal mission"
    for key, value in PRESETS[st.session_state.mission_preset].items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "seed_input" not in st.session_state:
        st.session_state.seed_input = 7


_initialize()


with st.sidebar:
    st.markdown(
        """
        <div class="brand-lockup">
          <span class="brand-mark"><span>✦</span></span>
          <span class="brand-name">AEROLAND</span>
          <div class="brand-sub">AUTONOMY OPERATIONS / V1.0</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-label">Navigation</div>', unsafe_allow_html=True)
    st.page_link("streamlit_app.py", label="Mission control")
    st.page_link("pages/Project_Guide.py", label="Project guide")
    st.markdown("---")
    st.markdown(
        """
        <div class="section-label">01 / Choose a mission</div>
        <div class="sidebar-copy">Start with a preset, then adjust individual controls only if you want to explore.</div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("HOW TO USE AEROLAND", expanded=True):
        st.markdown(
            """
            **1. Choose** a mission preset.

            **2. Adjust** wind, altitude, or safety limits if desired.

            **3. Press Run mission** to generate new telemetry.

            **4. Replay** the vehicle in the mission view at the top.

            **5. Scroll down** for charts, results, and downloads.
            """
        )
    live_health = _backend_health(MISSION_API_URL) if MISSION_API_CONFIGURED else {}
    live_available = (
        live_health.get("status") == "ok"
        and str(live_health.get("runner", "unknown")) == "gazebo"
    )
    runner_options = ["Browser digital twin"]
    if live_available:
        runner_options.append("Live Gazebo simulation")

    runner_mode = st.selectbox(
        "Simulation runner",
        runner_options,
        help="Browser mode is always available. Live Gazebo appears automatically when the simulator is online.",
    )
    live_mode = runner_mode.startswith("Live")
    backend_ready = live_available
    backend_runner = str(live_health.get("runner", "unknown"))
    st.selectbox(
        "Mission preset",
        list(PRESETS),
        key="mission_preset",
        on_change=_apply_preset,
        help="Presets provide useful starting points. Every value remains editable.",
    )
    st.markdown(
        f'<div class="preset-note">{html.escape(PRESET_DESCRIPTIONS[st.session_state.mission_preset])}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">02 / Flight conditions</div>', unsafe_allow_html=True)
    cruise_altitude = st.slider(
        "Cruise altitude (m)",
        min_value=1.50,
        max_value=4.00,
        step=0.10,
        key="altitude_input",
        help="The target altitude used during the inspection route.",
    )
    wind_speed = st.slider(
        "Wind disturbance (m/s)",
        min_value=0.0,
        max_value=8.0,
        step=0.10,
        key="wind_input",
        help="Choose any value from 0.00 to 8.00 m/s. Live Gazebo runs apply it as a horizontal disturbance.",
    )

    st.markdown('<div class="section-label">03 / Landing safety</div>', unsafe_allow_html=True)
    confidence_threshold = st.slider(
        "Minimum landing confidence",
        min_value=0.40,
        max_value=0.95,
        step=0.01,
        key="confidence_input",
        help="Descent pauses whenever confidence falls below this value.",
    )
    sigma_threshold = st.slider(
        "Maximum radial sigma (m)",
        min_value=0.05,
        max_value=0.30,
        step=0.01,
        key="sigma_input",
        help="Descent pauses whenever the estimated ground-plane uncertainty exceeds this limit.",
    )

    with st.expander("Advanced settings"):
        random_seed = st.number_input(
            "Simulation seed",
            min_value=0,
            max_value=2147483647,
            step=1,
            key="seed_input",
            help="Enter any whole number from 0 to 2,147,483,647. The same seed reproduces the same wind direction.",
        )
        st.caption("With wind above 0 m/s, the seed selects a repeatable disturbance direction. Telemetry updates at 10 Hz.")

    deploy = st.button(
        "Run mission",
        type="primary",
        disabled=live_mode and not backend_ready,
        width="stretch",
    )
    if live_mode:
        st.success("Live Gazebo simulation is ready. Wind and seed are configurable for every run.")

    st.markdown(
        f"""
        <div class="safety-envelope">
          <div class="section-label">04 / Active envelope</div>
          <div class="safety-row"><span class="safety-k">CONFIDENCE</span><span class="safety-v">≥ {confidence_threshold:.2f}</span></div>
          <div class="safety-row"><span class="safety-k">RADIAL SIGMA</span><span class="safety-v">≤ {sigma_threshold:.3f} m</span></div>
          <div class="safety-row"><span class="safety-k">WIND MODEL</span><span class="safety-v">{wind_speed:.2f} m/s</span></div>
          <div class="safety-row"><span class="safety-k">TELEMETRY</span><span class="safety-v">10 Hz</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.link_button(
        "Open source repository ↗",
        "https://github.com/shivalishrivastavaa/AeroLand",
        width="stretch",
    )


show_live_gazebo = live_mode and backend_ready and backend_runner == "gazebo"
if show_live_gazebo:
    st.markdown(
        """
        <div class="section-label">Live mission view / Gazebo</div>
        <div class="panel-heading">
          <span class="panel-title">Interactive PX4 simulation</span>
          <span class="panel-meta">GZWEB / 30 HZ SCENE LINK</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Press Run mission in the left panel. This view connects automatically; "
        "drag to orbit, scroll to zoom, or use Follow drone."
    )
    st.iframe(GAZEBO_VIEW_URL, height=650)


if deploy:
    configuration = MissionConfig(
        confidence_threshold=float(confidence_threshold),
        sigma_threshold_m=float(sigma_threshold),
        cruise_altitude_m=float(cruise_altitude),
        wind_speed_mps=float(wind_speed),
        random_seed=int(random_seed),
    )
    progress = st.progress(0, text="Initializing mission…")
    try:
        if live_mode:
            def update_backend_progress(value: float, state: str) -> None:
                progress.progress(
                    max(0, min(int(value * 100), 99)),
                    text=f"Mission: {state.replace('_', ' ').title()}…",
                )

            st.session_state.mission_result = run_remote_mission(
                MISSION_API_URL,
                configuration,
                progress_callback=update_backend_progress,
            )
        else:
            for value, label in [
                (18, "Loading inspection route…"),
                (42, "Propagating wind and camera disturbances…"),
                (68, "Evaluating uncertainty-gated descent…"),
                (88, "Compiling mission telemetry…"),
            ]:
                progress.progress(value, text=label)
                time.sleep(0.055)
            st.session_state.mission_result = run_mission(configuration)
        st.session_state.run_number += 1
        progress.progress(100, text="Mission run complete")
        time.sleep(0.08)
    except MissionAPIError:
        st.error(
            "The live mission could not finish. Please try again, or select "
            "Browser digital twin to continue without the live simulator."
        )
    finally:
        progress.empty()


result: MissionResult = st.session_state.mission_result
metrics = result.metrics
frame = result.telemetry
status = metrics["mission_status"]
status_class = "good" if status == "COMPLETE" else "bad"
source_labels = {
    "browser_digital_twin": ("BROWSER DT", "Synthetic browser telemetry"),
    "backend_demo": ("SERVICE DEMO", "Synthetic telemetry returned by the simulation service"),
    "gazebo_sitl": ("GAZEBO SITL", "Recorded PX4 SITL and Gazebo simulation telemetry"),
}
mode_status, model_disclosure = source_labels.get(
    result.source,
    (result.source.upper(), "Mission telemetry source is not recognized"),
)
risk_label, risk_class = _risk_label(result.configuration)
settings_pending = any(
    [
        abs(float(confidence_threshold) - result.configuration.confidence_threshold) > 1e-9,
        abs(float(sigma_threshold) - result.configuration.sigma_threshold_m) > 1e-9,
        abs(float(cruise_altitude) - result.configuration.cruise_altitude_m) > 1e-9,
        abs(float(wind_speed) - result.configuration.wind_speed_mps) > 1e-9,
        int(random_seed) != result.configuration.random_seed,
        live_mode != (result.source in {"backend_demo", "gazebo_sitl"}),
    ]
)
stack_badges = (
    '<span class="sys-item">ROS 2 <b>HUMBLE</b></span>'
    '<span class="sys-item">PX4 <b>SITL</b></span>'
    if result.source == "gazebo_sitl"
    else '<span class="sys-item">ENGINE <b>BROWSER</b></span>'
    '<span class="sys-item">MODE <b>INTERACTIVE</b></span>'
)

st.markdown(
    f"""
    <div class="ops-topbar">
      <div class="ops-path">AEROLAND / <strong>MISSION OPERATIONS</strong> / RUN {st.session_state.run_number:03d}</div>
      <div class="sys-array">
        <span class="sys-item"><i class="status-dot"></i>CONSOLE <b>ONLINE</b></span>
        <span class="sys-item"><i class="status-dot amber"></i>MODEL <b>{mode_status}</b></span>
        {stack_badges}
      </div>
    </div>
    <div class="hero-grid">
      <div>
        <div class="hero-kicker">Aerial autonomy / mission simulation</div>
        <h1 class="hero-title">MISSION<br><span>OPERATIONS.</span></h1>
        <p class="hero-copy">Run an autonomous aerial inspection, watch the vehicle return to its visual target, and see how confidence and uncertainty determine whether descent is allowed.</p>
      </div>
      <div class="hero-note"><strong>TELEMETRY SOURCE</strong>{html.escape(model_disclosure)}. Physical-flight validation is always reported separately.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not show_live_gazebo:
    st.markdown(
        """
        <div class="section-label">Animated mission view / browser twin</div>
        <div class="panel-heading">
          <span class="panel-title">Interactive X500-style mission playback</span>
          <span class="panel-meta">BROWSER NATIVE / NO INSTALLATION</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "The vehicle moves through the generated mission automatically. "
        "Pause, replay, scrub the timeline, drag to orbit, or scroll to zoom."
    )
    components.html(browser_twin_html(frame), height=650, scrolling=False)

if settings_pending:
    st.warning("Runner or settings changed. Press **Run mission** in the left panel to update the telemetry and results.")

replay_label = "Mission trace / replay" if show_live_gazebo else "Mission view / replay"
st.markdown(
    f'<div class="section-label">{replay_label}</div>',
    unsafe_allow_html=True,
)
st.caption("Drag the timeline to replay the mission. The 3D viewport and camera reticle update to the selected moment.")
playback_time = st.slider(
    "Mission playback",
    min_value=float(frame["elapsed_seconds"].min()),
    max_value=float(frame["elapsed_seconds"].max()),
    value=float(frame["elapsed_seconds"].max()),
    step=0.1,
    format="T+ %.1f s",
)
index = int((frame["elapsed_seconds"] - playback_time).abs().idxmin())
row = frame.iloc[index]
gate_class = "good" if bool(row["safe_to_descend"]) else "warn"
lock_class = "good" if bool(row["marker_detected"]) else "bad"
confidence_value = float(row["landing_confidence"])
sigma_value = float(row["marker_sigma_radial_m"]) if pd.notna(row["marker_sigma_radial_m"]) else 0.0

st.markdown(
    f"""
    <div class="readout-grid">
      <div class="readout"><div class="readout-k">MISSION STATE</div><div class="readout-v">{html.escape(str(row['mission_state']))}</div></div>
      <div class="readout"><div class="readout-k">ALTITUDE</div><div class="readout-v">{row['altitude_m']:.2f} m</div></div>
      <div class="readout"><div class="readout-k">VISUAL LOCK</div><div class="readout-v {lock_class}">{'TRACKING' if row['marker_detected'] else 'NO LOCK'}</div></div>
      <div class="readout"><div class="readout-k">CONF / σ</div><div class="readout-v">{confidence_value:.2f} / {sigma_value:.3f}</div></div>
      <div class="readout"><div class="readout-k">DESCENT GATE</div><div class="readout-v {gate_class}">{'APPROVED' if row['safe_to_descend'] else 'HOLD'}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

viewport_column, sensor_column = st.columns([1.48, 0.72], gap="small")
with viewport_column:
    _panel_heading("3D mission viewport", "LOCAL NED / TRACE REPLAY")
    st.plotly_chart(
        mission_view(frame, index),
        width="stretch",
        config={"displaylogo": False, "scrollZoom": True},
    )
with sensor_column:
    _panel_heading("Downward sensor", "ARUCO / NORMALIZED PLANE")
    st.plotly_chart(
        sensor_reticle(row),
        width="stretch",
        config={"displayModeBar": False},
    )

st.markdown('<br><div class="section-label">Mission data</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="status-ribbon">
      <div class="ribbon-cell"><span class="ribbon-k">Mission status</span><span class="ribbon-v {status_class}">{status}</span></div>
      <div class="ribbon-cell"><span class="ribbon-k">Runner</span><span class="ribbon-v">{html.escape(mode_status)}</span></div>
      <div class="ribbon-cell"><span class="ribbon-k">Telemetry</span><span class="ribbon-v good">{metrics['sample_count']} SAMPLES</span></div>
      <div class="ribbon-cell"><span class="ribbon-k">Descent gate</span><span class="ribbon-v">CONF + σ</span></div>
      <div class="ribbon-cell"><span class="ribbon-k">Scenario complexity</span><span class="ribbon-v {risk_class}">{risk_label}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(5, gap="small")
with metric_columns[0]:
    _metric_card("Mission duration", f"{metrics['mission_duration_s']:.1f} s", "<strong>10 Hz</strong> telemetry record")
with metric_columns[1]:
    error_color = "#67d391" if metrics["final_horizontal_error_m"] <= 0.05 else "#d6a34a"
    _metric_card(
        "Landing error",
        f"{100 * metrics['final_horizontal_error_m']:.1f} cm",
        "Horizontal target offset",
        error_color,
    )
with metric_columns[2]:
    _metric_card(
        "Mean confidence",
        f"{metrics['mean_landing_confidence']:.3f}",
        f"Limit <strong>≥ {result.configuration.confidence_threshold:.2f}</strong>",
        "#f2f0ea",
    )
with metric_columns[3]:
    _metric_card(
        "Mean radial sigma",
        f"{metrics['mean_ground_sigma_m']:.3f} m",
        f"Limit <strong>≤ {result.configuration.sigma_threshold_m:.3f} m</strong>",
        "#c8a7ff",
    )
with metric_columns[4]:
    _metric_card(
        "Descent approval",
        f"{metrics['descent_approval_pct']:.1f}%",
        f"<strong>{metrics['uncertainty_pause_events']}</strong> safety pauses",
        "#d6a34a",
    )

telemetry_tab, analysis_tab, system_tab = st.tabs(["FLIGHT DATA", "RESULTS", "SYSTEM"])


with telemetry_tab:
    first_row = st.columns(2, gap="small")
    with first_row[0]:
        st.plotly_chart(altitude_chart(frame), width="stretch", config={"displaylogo": False})
    with first_row[1]:
        st.plotly_chart(
            confidence_chart(frame, result.configuration.confidence_threshold),
            width="stretch",
            config={"displaylogo": False},
        )
    second_row = st.columns(2, gap="small")
    with second_row[0]:
        st.plotly_chart(
            sigma_chart(frame, result.configuration.sigma_threshold_m),
            width="stretch",
            config={"displaylogo": False},
        )
    with second_row[1]:
        st.plotly_chart(state_chart(frame), width="stretch", config={"displaylogo": False})
    st.plotly_chart(error_chart(frame), width="stretch", config={"displaylogo": False})


with analysis_tab:
    verdict_color = "#6fdc9b" if status == "COMPLETE" else "#ff6078"
    verdict_copy = (
        f"The vehicle completed the mission with {metrics['uncertainty_pause_events']} uncertainty-gated holds "
        f"and a final target offset of {100 * metrics['final_horizontal_error_m']:.1f} cm."
        if status == "COMPLETE"
        else "The browser model exhausted the mission window because the selected safety envelope could not be satisfied."
    )
    st.markdown(
        f"""
        <div class="verdict" style="--verdict-color:{verdict_color}">
          <div><div class="verdict-k">MISSION VERDICT</div><div class="verdict-v">{status}</div></div>
          <div class="verdict-copy">{html.escape(verdict_copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="interpretation">
          <strong>PLAIN-LANGUAGE INTERPRETATION</strong>
          <p>{html.escape(_interpretation(result))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    result_left, result_right = st.columns([1.28, 0.72], gap="large")
    with result_left:
        _panel_heading("Generated mission report", "PNG / 170 DPI")
        report_png = render_report_png(result)
        st.image(report_png, width="stretch")
    with result_right:
        _panel_heading("Event record", "STATE + SAFETY TRANSITIONS")
        events = event_log(frame)
        st.dataframe(
            events,
            width="stretch",
            hide_index=True,
            height=440,
            column_config={
                "T+": st.column_config.TextColumn(width="small"),
                "Event": st.column_config.TextColumn(width="medium"),
                "Status": st.column_config.TextColumn(width="medium"),
                "Detail": st.column_config.TextColumn(width="large"),
            },
        )

    st.markdown('<div class="section-label">Data products</div>', unsafe_allow_html=True)
    download_columns = st.columns(4, gap="small")
    with download_columns[0]:
        st.download_button(
            "Download complete bundle",
            data=result_bundle(result),
            file_name="aeroland_results.zip",
            mime="application/zip",
            width="stretch",
        )
    with download_columns[1]:
        st.download_button(
            "Telemetry CSV",
            data=frame.to_csv(index=False),
            file_name="telemetry.csv",
            mime="text/csv",
            width="stretch",
        )
    with download_columns[2]:
        st.download_button(
            "Technical report PNG",
            data=report_png,
            file_name="mission_report.png",
            mime="image/png",
            width="stretch",
        )
    with download_columns[3]:
        st.download_button(
            "Summary TXT",
            data=summary_text(result),
            file_name="summary.txt",
            mime="text/plain",
            width="stretch",
        )

with system_tab:
    st.markdown(
        """
        <div class="section-label">Closed-loop system architecture</div>
        <div class="architecture">
          <div class="arch-node"><div class="arch-index">01 / SENSE</div><div class="arch-title">DOWNWARD CAMERA</div><div class="arch-copy">Gazebo image stream or deterministic browser sensor model.</div></div>
          <div class="arch-node"><div class="arch-index">02 / PERCEIVE</div><div class="arch-title">ARUCO DETECTOR</div><div class="arch-copy">Marker availability and normalized image-plane centering error.</div></div>
          <div class="arch-node"><div class="arch-index">03 / ESTIMATE</div><div class="arch-title">UNCERTAINTY</div><div class="arch-copy">Rolling confidence and ground-plane radial sigma.</div></div>
          <div class="arch-node"><div class="arch-index">04 / DECIDE</div><div class="arch-title">SAFETY GATE</div><div class="arch-copy">Approve, pause, recover, or abort against explicit limits.</div></div>
          <div class="arch-node"><div class="arch-index">05 / ACT</div><div class="arch-title">PX4 CONTROL</div><div class="arch-copy">Offboard setpoints, descent hold, and landing handoff.</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    verified_columns = st.columns([0.9, 1.1], gap="large")
    with verified_columns[0]:
        st.markdown('<div class="section-label">Verified Gazebo benchmark</div>', unsafe_allow_html=True)
        benchmark_metrics = st.columns(2)
        with benchmark_metrics[0]:
            _metric_card("Landing error", "3.6 cm", "Recorded PX4 SITL mission", "#6fdc9b")
        with benchmark_metrics[1]:
            _metric_card("Mean confidence", "0.818", "Recorded descent guidance", "#f2f0ea")
        st.markdown("<br>", unsafe_allow_html=True)
        benchmark_metrics_2 = st.columns(2)
        with benchmark_metrics_2[0]:
            _metric_card("Mean radial sigma", "0.033 m", "Recorded ground plane", "#c8a7ff")
        with benchmark_metrics_2[1]:
            _metric_card("Safety pauses", "3", "Closed-loop descent holds", "#d6a34a")
    with verified_columns[1]:
        st.markdown('<div class="section-label">Runtime separation</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="disclosure"><strong>BROWSER DIGITAL TWIN</strong><br>Runs immediately inside Streamlit. It is deterministic, parameterized, and useful for interface testing and safety-envelope exploration. Its results are synthetic.</div><br>
            <div class="disclosure"><strong>LIVE SIMULATION</strong><br>When enabled by the site operator, AeroLand runs the ROS 2 mission with PX4 SITL and Gazebo. Visitors do not need to configure these services. Every result is labeled with its actual telemetry source.</div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Telemetry contract"):
            st.code(
                "elapsed_seconds, mission_state, x_m, y_m, z_ned_m, altitude_m,\n"
                "marker_detected, marker_error_x, marker_error_y, marker_error_norm,\n"
                "landing_confidence, marker_sigma_x_m, marker_sigma_y_m,\n"
                "marker_sigma_radial_m, safe_to_descend",
                language="text",
            )

st.markdown(
    """
    <div style="margin-top:2.5rem;padding-top:1rem;border-top:1px solid #292825;display:flex;justify-content:space-between;gap:1rem;color:#7f7b73;font:0.59rem ui-monospace,monospace;letter-spacing:.08em;">
      <span>AEROLAND / UNCERTAINTY-AWARE AUTONOMY</span><span>DESIGNED + ENGINEERED BY SHIVALI SHRIVASTAVA</span>
    </div>
    """,
    unsafe_allow_html=True,
)
