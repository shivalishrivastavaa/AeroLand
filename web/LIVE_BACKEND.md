# AeroLand Local Mission Backend

This guide connects the mission console to the existing ROS 2, PX4 SITL, and
Gazebo workspace. Complete the API integration test first, then switch the
same service to the real simulator.

## What was added

The website now talks to a validated mission API instead of accepting commands
from browser users. The service supports two server-controlled modes:

| Mode | Purpose | Telemetry label |
| --- | --- | --- |
| `demo` | Test the website/API connection without ROS or Gazebo | API TEST |
| `gazebo` | Launch the local headless PX4/Gazebo and AeroLand mission | GAZEBO SITL |

The browser cannot select the backend's execution mode. Only the operator who
starts the service can choose it through `AEROLAND_RUNNER_MODE`.

## Step 1: rebuild the updated ROS workspace

The launch stack now accepts cruise altitude, confidence threshold, and radial
sigma threshold from the website.

```bash
cd ~/aeroland_ws
source /opt/ros/humble/setup.bash

PYTHONNOUSERSITE=1 colcon build --symlink-install
source install/setup.bash
```

## Step 2: create the website environment

```bash
cd ~/aeroland_ws/web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Do this once. On later sessions, only activate the existing environment.

## Step 3: test the API connection

Open Ubuntu Terminal 1:

```bash
cd ~/aeroland_ws/web
source .venv/bin/activate

export AEROLAND_RUNNER_MODE=demo
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open Ubuntu Terminal 2:

```bash
cd ~/aeroland_ws/web
source .venv/bin/activate

export AEROLAND_SIM_API_URL=http://127.0.0.1:8000
streamlit run streamlit_app.py
```

In the website:

1. Set **Simulation runner** to **Local mission backend**.
2. Confirm the sidebar says the backend is in API integration-test mode.
3. Press **Run mission**.
4. Confirm the top status reads **API TEST**.

This proves the website/API/result pipeline works. It does not yet claim that
Gazebo ran.

## Step 4: verify the real-run prerequisites

Stop Terminal 1 with `Ctrl+C`, then run:

```bash
source /opt/ros/humble/setup.bash
source ~/aeroland_ws/install/setup.bash

command -v ros2
command -v MicroXRCEAgent
test -f ~/PX4-Autopilot/Makefile && echo "PX4 checkout found"
test -f ~/aeroland_ws/install/setup.bash && echo "AeroLand build found"
```

All four checks must succeed.

## Step 5: start the real Gazebo runner

In Terminal 1:

```bash
source /opt/ros/humble/setup.bash
source ~/aeroland_ws/install/setup.bash
source ~/aeroland_ws/web/.venv/bin/activate

export AEROLAND_RUNNER_MODE=gazebo
export AEROLAND_WORKSPACE=~/aeroland_ws
export PX4_AUTOPILOT_DIR=~/PX4-Autopilot
export AEROLAND_START_XRCE=1
export AEROLAND_MISSION_TIMEOUT=180

cd ~/aeroland_ws/web
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Do not separately start Micro XRCE-DDS Agent, PX4, Gazebo, or the AeroLand ROS
launch. The mission service owns those processes and stops them after every
run.

Check readiness from another terminal:

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

The response should contain:

```json
{
  "status": "ok",
  "runner": "gazebo"
}
```

If `status` is `not_ready`, the `detail` field names the missing path or
command.

## Step 6: run a genuine mission from the website

Keep Terminal 2 running the Streamlit website. Refresh the page, then:

1. Select **Local mission backend**.
2. Confirm the sidebar says **PX4/Gazebo backend ready**.
3. Select **Nominal mission**.
4. Set **Wind disturbance** to `0.0 m/s`.
5. Keep **Simulation seed** at `7`.
6. Press **Run mission** once.

The service will start Micro XRCE-DDS Agent, headless Gazebo, PX4 SITL, and the
AeroLand ROS launch. It watches the mission CSV until the controller publishes
`COMPLETE`, stops the simulator processes, and returns the recorded telemetry
to the site. The top status and downloaded report will read **GAZEBO SITL**.

Run files are retained at:

```text
~/.aeroland/runs/<run-id>/
```

Each directory contains telemetry plus separate XRCE, PX4/Gazebo, and AeroLand
logs for debugging.

## Current safety limits

- Only one Gazebo mission can run at a time.
- Every mission is terminated after 180 seconds by default.
- The current `aruco` world has no validated wind plugin, so real runs require
  `0.0 m/s` wind.
- The browser seed does not yet control Gazebo, so real runs require seed `7`.
- The real runner is local-only and binds its API to `127.0.0.1`.
- Results are simulation evidence, never physical-flight validation.
- Camera streaming is the next backend milestone; this version returns the
  recorded mission telemetry after completion.

## Troubleshooting

### Port 8888 is already in use

Another Micro XRCE-DDS Agent may already be running. Stop it, or tell the API
to use the existing agent:

```bash
export AEROLAND_START_XRCE=0
```

### Backend says `ros2 is not on PATH`

Stop the API, source ROS before activating the web environment, then restart:

```bash
source /opt/ros/humble/setup.bash
source ~/aeroland_ws/install/setup.bash
source ~/aeroland_ws/web/.venv/bin/activate
```

### A real mission fails

Use the run ID shown in the downloaded summary or API status, then inspect:

```bash
ls ~/.aeroland/runs/<run-id>
less ~/.aeroland/runs/<run-id>/px4_gazebo.log
less ~/.aeroland/runs/<run-id>/aeroland.log
```

### Return to the safe API test

```bash
export AEROLAND_RUNNER_MODE=demo
```

Restart the API. The website will label the next result **API TEST**.
