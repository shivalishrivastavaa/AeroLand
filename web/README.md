# AeroLand Mission Operations Console

Interactive Streamlit interface for the AeroLand uncertainty-aware aerial
inspection and precision-landing project.

## What is included

- Black space-operations visual system
- Guided four-step mission setup and scenario presets
- Sidebar quick start and complete operator guide
- Mission replay at the top with metrics, telemetry, and reports below
- Deterministic browser digital-twin mission runner
- Wind-dependent vehicle, camera, confidence, and uncertainty behavior
- Interactive 3-D mission playback and landing-sensor reticle
- Altitude, confidence, safety-gate, sigma, state, and marker-error plots
- State and safety-event record
- Downloadable telemetry, summary, event log, PNG report, and result bundle
- Explicit separation between synthetic browser data and verified Gazebo data
- Validated local mission API with asynchronous status and telemetry endpoints
- Server-controlled demo and real headless PX4/Gazebo runner modes
- Honest result-source labeling across the console, reports, and downloads

## Run locally

```bash
cd ~/aeroland_ws/web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open <http://localhost:8501>.

See [HOW_TO.md](HOW_TO.md) for the complete operator guide.

To connect the console to the local PX4/Gazebo stack, follow
[LIVE_BACKEND.md](LIVE_BACKEND.md). Start with API test mode before enabling the
real simulator.

## Test

```bash
cd ~/aeroland_ws/web
source .venv/bin/activate
python -m pytest -q
```

## Data integrity note

The browser runner is a deterministic, parameterized demonstrator. Its
telemetry is synthetic and is labeled as such in the interface, summaries,
and downloads. The separately labeled 3.6 cm benchmark was measured in the
project's PX4 SITL and Gazebo mission. Backend results are labeled `API TEST`
or `GAZEBO SITL` according to the runner that actually produced their
telemetry.
