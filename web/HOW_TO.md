# How to Use the AeroLand Mission Console

## Start the website

```bash
cd ~/aeroland_ws/web
source .venv/bin/activate
streamlit run streamlit_app.py
```

Open <http://localhost:8501> and keep the Ubuntu terminal running.

For the local mission service and the real Gazebo connection, follow
[LIVE_BACKEND.md](LIVE_BACKEND.md).

## Run your first mission

1. Keep **Simulation runner** set to **Browser digital twin**.
2. Select **Nominal mission**.
3. Press **Run mission**.
4. Use the mission view at the top and drag the playback timeline.
5. Scroll to **Results** to read the explanation and event log.
6. Select **Download complete bundle** to save all mission products.

## Mission presets

| Preset | Purpose |
| --- | --- |
| Nominal mission | Recommended first run with default safety limits |
| Crosswind evaluation | Demonstrates how moderate wind affects the mission |
| Conservative safety | Uses stricter confidence and uncertainty limits |
| Stress test | Exercises holds, recovery behavior, and possible aborts |

## Controls

- **Cruise altitude:** Target height during the inspection route.
- **Wind disturbance:** Increases drift, camera error, uncertainty, recovery
  activity, mission time, and abort risk.
- **Minimum landing confidence:** Descent is rejected below this value.
- **Maximum radial sigma:** Descent is rejected above this uncertainty value.
- **Simulation seed:** Makes a configuration exactly reproducible.

Higher confidence limits and lower sigma limits are more conservative.

## Read the mission

- **Mission view:** Appears at the top and replays the 3-D route and
  downward-camera target view.
- **Flight Data:** Shows altitude, confidence, descent approval, uncertainty,
  mission state, and marker-centering error.
- **Results:** Explains the outcome and provides the event log, report, and
  downloads.
- **Sidebar How To:** Provides the five essential operating steps beside the
  controls.
- **System:** Shows the architecture and separates synthetic results from the
  verified PX4/Gazebo benchmark.

## Compare two runs fairly

1. Keep the simulation seed unchanged.
2. Run **Nominal mission** and download its result bundle.
3. Run **Crosswind evaluation** with the same seed.
4. Compare duration, landing error, uncertainty, approval rate, pauses, and
   recovery events.

## Downloaded result bundle

The ZIP contains:

- `telemetry.csv`
- `summary.txt`
- `configuration.json`
- `event_log.csv`
- `mission_report.png`
- `README.txt`

## Important model distinction

The browser runner produces synthetic telemetry. The local mission service is
also synthetic when configured in `demo` mode and is labeled **API TEST**. Only
the service's `gazebo` mode launches PX4 SITL and Gazebo; those results are
labeled **GAZEBO SITL**. None of these modes represents physical flight.

## Troubleshooting

- If the page does not open, confirm the terminal still shows Streamlit as
  running and reopen <http://localhost:8501>.
- If results did not change after moving a control, press **Run mission**.
- If dependencies are missing, activate `.venv` and run
  `pip install -r requirements.txt`.
- Stop the local website with `Ctrl+C` in its Ubuntu terminal.
