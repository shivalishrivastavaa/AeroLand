"""Mission runners for API integration tests and real local Gazebo SITL."""

from __future__ import annotations

import os
from pathlib import Path
import math
import random
import shutil
import shlex
import signal
import subprocess
import sys
from threading import Event, Lock
import time
from typing import Callable

import pandas as pd

from aeroland_web.simulation import (
    MissionConfig,
    MissionResult,
    mission_result_from_telemetry,
    run_mission,
)


ProgressCallback = Callable[[float, str], None]


class RunnerError(RuntimeError):
    """Raised when a mission runner cannot safely complete a run."""


class MissionCancelled(RunnerError):
    """Raised when an operator cancels a mission."""


class DemoRunner:
    """Exercise the complete API contract without claiming Gazebo telemetry."""

    name = "demo"
    supports_wind = True
    supports_seed = True

    def health(self) -> tuple[bool, str]:
        return True, "Mission API is ready in synthetic integration-test mode."

    def gazebo_view_status(self) -> dict[str, bool | str]:
        return {
            "ready": False,
            "state": "unavailable",
            "detail": "The live Gazebo view is available only with the Gazebo runner.",
        }

    def run(
        self,
        run_id: str,
        config: MissionConfig,
        cancel_event: Event,
        progress: ProgressCallback,
    ) -> MissionResult:
        for value, state in [
            (0.10, "INITIALIZING"),
            (0.32, "STARTING MODEL"),
            (0.68, "RUNNING MISSION"),
            (0.92, "COMPILING TELEMETRY"),
        ]:
            if cancel_event.is_set():
                raise MissionCancelled("Mission cancelled by operator")
            progress(value, state)
            time.sleep(0.04)
        result = run_mission(config)
        result.source = "backend_demo"
        result.run_id = run_id
        return result


class GazeboRunner:
    """Launch one PX4/Gazebo mission and collect its ROS CSV log."""

    name = "gazebo"
    supports_wind = True
    supports_seed = True
    _mission_lock = Lock()

    def __init__(self) -> None:
        self.workspace = Path(
            os.getenv("AEROLAND_WORKSPACE", "~/aeroland_ws")
        ).expanduser().resolve()
        self.px4_directory = Path(
            os.getenv("PX4_AUTOPILOT_DIR", "~/PX4-Autopilot")
        ).expanduser().resolve()
        self.run_root = Path(
            os.getenv("AEROLAND_RUN_DIRECTORY", "~/.aeroland/runs")
        ).expanduser().resolve()
        self.timeout_seconds = int(os.getenv("AEROLAND_MISSION_TIMEOUT", "180"))
        self.start_xrce = os.getenv("AEROLAND_START_XRCE", "1") != "0"
        self.start_gcs_heartbeat = (
            os.getenv("AEROLAND_START_GCS_HEARTBEAT", "1") != "0"
        )
        self.gazebo_headless = (
            os.getenv("AEROLAND_GAZEBO_HEADLESS", "0") == "1"
        )
        self.web_directory = Path(__file__).resolve().parents[1]
        self.start_gzweb = os.getenv("AEROLAND_START_GZWEB", "1") != "0"
        self.gzweb_launch_file = Path(
            os.getenv(
                "AEROLAND_GZWEB_LAUNCH_FILE",
                str(self.web_directory / "gazebo_view" / "websocket.gzlaunch"),
            )
        ).expanduser().resolve()
        self._gzweb_ready = Event()
        self._gzweb_client_ready = Event()
        self._gzweb_problem: str | None = None
        self.gzweb_client_wait_seconds = max(
            0.0,
            float(os.getenv("AEROLAND_GZWEB_CLIENT_WAIT_SECONDS", "25")),
        )
        self.gzweb_postflight_seconds = max(
            0.0,
            float(os.getenv("AEROLAND_GZWEB_POSTFLIGHT_SECONDS", "15")),
        )

    def gazebo_view_status(self) -> dict[str, bool | str]:
        if self._gzweb_ready.is_set():
            return {
                "ready": True,
                "state": "ready",
                "client_ready": self._gzweb_client_ready.is_set(),
                "detail": (
                    "The embedded drone model is rendered."
                    if self._gzweb_client_ready.is_set()
                    else "Gazebo is ready; loading the embedded drone model."
                ),
            }
        if self._gzweb_problem:
            return {
                "ready": False,
                "state": "unavailable",
                "detail": self._gzweb_problem,
            }
        return {
            "ready": False,
            "state": "waiting",
            "client_ready": False,
            "detail": "Waiting for a local Gazebo mission to publish telemetry.",
        }

    def gazebo_view_client_ready(self) -> dict[str, bool | str]:
        """Record that the browser has rendered at least one drone mesh."""

        accepted = self._gzweb_ready.is_set()
        if accepted:
            self._gzweb_client_ready.set()
        return {
            "accepted": accepted,
            "client_ready": self._gzweb_client_ready.is_set(),
        }

    def health(self) -> tuple[bool, str]:
        problems: list[str] = []
        if not (self.workspace / "install" / "setup.bash").is_file():
            problems.append(f"missing {self.workspace / 'install/setup.bash'}")
        if not (self.px4_directory / "Makefile").is_file():
            problems.append(f"missing PX4 checkout at {self.px4_directory}")
        for resource_directory in self._px4_gazebo_resource_directories():
            if not resource_directory.is_dir():
                problems.append(f"missing PX4 Gazebo resources at {resource_directory}")
        for command in ["bash", "make", "ros2"]:
            if shutil.which(command) is None:
                problems.append(f"{command} is not on PATH")
        if self.start_xrce and shutil.which("MicroXRCEAgent") is None:
            problems.append("MicroXRCEAgent is not on PATH")
        if self.start_gcs_heartbeat:
            try:
                import pymavlink  # noqa: F401
            except ImportError:
                problems.append("pymavlink is not installed in the API environment")
        if self.start_gzweb:
            if shutil.which("gz") is None:
                problems.append("gz is not on PATH")
            if not self.gzweb_launch_file.is_file():
                problems.append(f"missing {self.gzweb_launch_file}")
        if self.gazebo_headless is False and not (
            os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")
        ):
            problems.append(
                "visible Gazebo requested but DISPLAY/WAYLAND_DISPLAY is unavailable"
            )
        if problems:
            return False, "; ".join(problems)
        return True, "ROS 2, PX4 SITL, Gazebo runner, and workspace are available."

    @staticmethod
    def _terminate(process: subprocess.Popen | None) -> None:
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=8)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @staticmethod
    def _latest_telemetry(log_directory: Path) -> Path | None:
        files = sorted(
            log_directory.glob("aeroland_mission_*.csv"),
            key=lambda path: path.stat().st_mtime,
        )
        return files[-1] if files else None

    @staticmethod
    def _read_state(path: Path | None) -> tuple[str, pd.DataFrame | None]:
        if path is None:
            return "WAITING FOR TELEMETRY", None
        try:
            frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
            return "WAITING FOR TELEMETRY", None
        if frame.empty or "mission_state" not in frame:
            return "WAITING FOR TELEMETRY", None
        state = str(frame.iloc[-1]["mission_state"])
        return state, frame

    @staticmethod
    def _progress_for_state(state: str) -> float:
        values = {
            "WAITING FOR TELEMETRY": 0.12,
            "UNKNOWN": 0.15,
            "WAITING": 0.18,
            "PRESTREAM": 0.23,
            "ACTIVATE": 0.28,
            "TAKEOFF": 0.36,
            "INSPECTION": 0.55,
            "SEARCH": 0.68,
            "ALIGN": 0.75,
            "DESCEND": 0.86,
            "RECOVER": 0.78,
            "LANDING": 0.94,
            "COMPLETE": 1.0,
        }
        return values.get(state, 0.15)

    def _px4_gazebo_resource_directories(self) -> tuple[Path, Path]:
        """Return the model and world directories used by PX4 Gazebo SITL."""

        simulation_directory = self.px4_directory / "Tools" / "simulation" / "gz"
        return simulation_directory / "models", simulation_directory / "worlds"

    def _gazebo_environment(self) -> dict[str, str]:
        """Expose PX4 meshes and textures to Gazebo and the browser bridge."""

        environment = os.environ.copy()
        models_directory, worlds_directory = (
            self._px4_gazebo_resource_directories()
        )
        px4_resource_paths = [str(models_directory), str(worlds_directory)]

        existing_paths = [
            item
            for item in environment.get("GZ_SIM_RESOURCE_PATH", "").split(
                os.pathsep
            )
            if item
        ]
        combined_paths = list(
            dict.fromkeys([*px4_resource_paths, *existing_paths])
        )

        environment["PX4_GZ_MODELS"] = str(models_directory)
        environment["PX4_GZ_WORLDS"] = str(worlds_directory)
        environment["GZ_SIM_RESOURCE_PATH"] = os.pathsep.join(combined_paths)
        return environment

    def _start_process(
        self,
        command: list[str],
        *,
        log_path: Path,
        cwd: Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> tuple[subprocess.Popen, object]:
        handle = log_path.open("wb")
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return process, handle

    @staticmethod
    def _gazebo_scene_service_ready(environment: dict[str, str]) -> bool:
        """Return true once Gazebo is publishing the ArUco world scene."""

        try:
            result = subprocess.run(
                ["gz", "service", "-l"],
                env=environment,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return "/world/aruco/scene/info" in result.stdout

    def _wind_plugin_configured(self) -> bool:
        """Confirm that this PX4 checkout loads Gazebo's wrench system."""

        server_config = (
            self.px4_directory
            / "src"
            / "modules"
            / "simulation"
            / "gz_bridge"
            / "server.config"
        )
        try:
            source = server_config.read_text(encoding="utf-8")
        except OSError:
            return False
        return "gz-sim-apply-link-wrench-system" in source

    @staticmethod
    def _wind_wrench(config: MissionConfig) -> tuple[float, float, float]:
        """Convert wind speed and seed into a repeatable horizontal force.

        The force uses the standard drag approximation 0.5 * rho * CdA * v^2.
        The X/Y direction comes from a private RNG so the same seed produces the
        same disturbance without changing random state elsewhere in the app.
        """

        direction_radians = random.Random(config.random_seed).uniform(
            -math.pi, math.pi
        )
        air_density_kg_m3 = 1.225
        effective_drag_area_m2 = 0.035
        force_newtons = (
            0.5
            * air_density_kg_m3
            * effective_drag_area_m2
            * config.wind_speed_mps**2
        )
        return (
            force_newtons * math.cos(direction_radians),
            force_newtons * math.sin(direction_radians),
            math.degrees(direction_radians) % 360.0,
        )

    @classmethod
    def _wind_command(cls, config: MissionConfig) -> list[str] | None:
        """Build the Gazebo persistent-wrench publisher for one mission."""

        if config.wind_speed_mps <= 0.0:
            return None
        force_x, force_y, _ = cls._wind_wrench(config)
        message = (
            'entity: {name: "x500_mono_cam_down_0", type: MODEL}, '
            "wrench: {"
            f"force: {{x: {force_x:.9f}, y: {force_y:.9f}, z: 0.0}}, "
            "torque: {x: 0.0, y: 0.0, z: 0.0}}"
        )
        return [
            "gz",
            "topic",
            "-t",
            "/world/aruco/wrench/persistent",
            "-m",
            "gz.msgs.EntityWrench",
            "-p",
            message,
        ]

    def run(
        self,
        run_id: str,
        config: MissionConfig,
        cancel_event: Event,
        progress: ProgressCallback,
    ) -> MissionResult:
        ready, detail = self.health()
        if not ready:
            raise RunnerError(f"Gazebo runner is not ready: {detail}")
        if config.wind_speed_mps > 0.0 and not self._wind_plugin_configured():
            raise RunnerError(
                "This PX4 checkout does not configure Gazebo's persistent-wrench "
                "system, so a non-zero wind disturbance cannot be applied."
            )
        if not self._mission_lock.acquire(blocking=False):
            raise RunnerError("Another Gazebo mission is already running")

        run_directory = self.run_root / run_id
        log_directory = run_directory / "telemetry"
        log_directory.mkdir(parents=True, exist_ok=False)
        processes: list[subprocess.Popen] = []
        handles: list[object] = []
        px4_process: subprocess.Popen | None = None
        ros_process: subprocess.Popen | None = None
        gzweb_process: subprocess.Popen | None = None
        self._gzweb_ready.clear()
        self._gzweb_client_ready.clear()
        self._gzweb_problem = None

        try:
            progress(0.04, "STARTING DDS AGENT")
            if self.start_xrce:
                agent, handle = self._start_process(
                    ["MicroXRCEAgent", "udp4", "-p", "8888"],
                    log_path=run_directory / "xrce.log",
                )
                processes.append(agent)
                handles.append(handle)

            if self.start_gcs_heartbeat:
                progress(0.06, "STARTING GCS HEARTBEAT")
                heartbeat, handle = self._start_process(
                    [sys.executable, "-m", "backend.gcs_heartbeat"],
                    cwd=self.web_directory,
                    log_path=run_directory / "gcs_heartbeat.log",
                )
                processes.append(heartbeat)
                handles.append(handle)

            progress(0.08, "STARTING PX4 + GAZEBO")
            px4_environment = self._gazebo_environment()
            px4_environment["PX4_GZ_WORLD"] = "aruco"
            if self.gazebo_headless:
                px4_environment["HEADLESS"] = "1"
            else:
                px4_environment.pop("HEADLESS", None)
            px4_process, handle = self._start_process(
                ["make", "px4_sitl", "gz_x500_mono_cam_down"],
                cwd=self.px4_directory,
                environment=px4_environment,
                log_path=run_directory / "px4_gazebo.log",
            )
            processes.append(px4_process)
            handles.append(handle)

            if self.start_gzweb:
                progress(0.10, "STARTING EMBEDDED GAZEBO VIEW")
                gzweb_environment = self._gazebo_environment()
                gzweb_process, handle = self._start_process(
                    ["gz", "launch", "-v", "3", str(self.gzweb_launch_file)],
                    environment=gzweb_environment,
                    log_path=run_directory / "gzweb_bridge.log",
                )
                processes.append(gzweb_process)
                handles.append(handle)
                time.sleep(0.8)
                if gzweb_process.poll() is not None:
                    self._gzweb_problem = (
                        "The optional browser bridge stopped. The flight mission is "
                        "continuing in the desktop Gazebo window; inspect "
                        f"{run_directory / 'gzweb_bridge.log'}."
                    )
                    gzweb_process = None

            if gzweb_process is not None:
                progress(0.11, "WAITING FOR GAZEBO SCENE")
                scene_deadline = time.monotonic() + 30.0
                while time.monotonic() < scene_deadline:
                    if cancel_event.is_set():
                        raise MissionCancelled("Mission cancelled by operator")
                    if px4_process.poll() is not None:
                        raise RunnerError(
                            "PX4/Gazebo stopped while preparing the embedded view; "
                            f"inspect {run_directory / 'px4_gazebo.log'}"
                        )
                    if gzweb_process.poll() is not None:
                        self._gzweb_problem = (
                            "The optional browser bridge stopped while preparing "
                            "the embedded view; inspect "
                            f"{run_directory / 'gzweb_bridge.log'}."
                        )
                        gzweb_process = None
                        break
                    if self._gazebo_scene_service_ready(gzweb_environment):
                        self._gzweb_ready.set()
                        break
                    time.sleep(0.5)

            if gzweb_process is not None and self._gzweb_ready.is_set():
                progress(0.12, "LOADING EMBEDDED DRONE")
                client_deadline = (
                    time.monotonic() + self.gzweb_client_wait_seconds
                )
                while (
                    not self._gzweb_client_ready.is_set()
                    and time.monotonic() < client_deadline
                ):
                    if cancel_event.is_set():
                        raise MissionCancelled("Mission cancelled by operator")
                    if px4_process.poll() is not None:
                        raise RunnerError(
                            "PX4/Gazebo stopped while loading the embedded drone; "
                            f"inspect {run_directory / 'px4_gazebo.log'}"
                        )
                    if gzweb_process.poll() is not None:
                        self._gzweb_ready.clear()
                        self._gzweb_problem = (
                            "The optional browser bridge disconnected while loading "
                            "the embedded drone; inspect "
                            f"{run_directory / 'gzweb_bridge.log'}."
                        )
                        gzweb_process = None
                        break
                    time.sleep(0.25)

            wind_command = self._wind_command(config)
            if wind_command is not None:
                progress(0.13, "APPLYING SEEDED WIND DISTURBANCE")
                wind_deadline = time.monotonic() + 30.0
                while time.monotonic() < wind_deadline:
                    if cancel_event.is_set():
                        raise MissionCancelled("Mission cancelled by operator")
                    if px4_process.poll() is not None:
                        raise RunnerError(
                            "PX4/Gazebo stopped while preparing the wind "
                            f"disturbance; inspect {run_directory / 'px4_gazebo.log'}"
                        )
                    if self._gazebo_scene_service_ready(px4_environment):
                        break
                    time.sleep(0.5)
                else:
                    raise RunnerError(
                        "Gazebo did not finish loading before the wind disturbance; "
                        f"inspect {run_directory / 'px4_gazebo.log'}"
                    )

                force_x, force_y, direction_degrees = self._wind_wrench(config)
                (run_directory / "wind_disturbance.txt").write_text(
                    "AeroLand seeded wind-equivalent disturbance\n"
                    f"speed_mps={config.wind_speed_mps:.3f}\n"
                    f"seed={config.random_seed}\n"
                    f"direction_degrees={direction_degrees:.3f}\n"
                    f"force_x_newtons={force_x:.9f}\n"
                    f"force_y_newtons={force_y:.9f}\n",
                    encoding="utf-8",
                )
                wind_process, handle = self._start_process(
                    wind_command,
                    environment=px4_environment,
                    log_path=run_directory / "wind_publisher.log",
                )
                processes.append(wind_process)
                handles.append(handle)
                time.sleep(0.35)
                if (
                    wind_process.poll() is not None
                    and wind_process.returncode not in (0, None)
                ):
                    raise RunnerError(
                        "Gazebo rejected the requested wind disturbance; inspect "
                        f"{run_directory / 'wind_publisher.log'}"
                    )

            progress(0.14, "STARTING AEROLAND")
            ros_command = (
                "source /opt/ros/humble/setup.bash && "
                f"source {shlex.quote(str(self.workspace / 'install/setup.bash'))} && "
                "PYTHONNOUSERSITE=1 ros2 launch "
                "aeroland_bringup inspection_mission.launch.py "
                "start_mission:=true "
                f"log_directory:={shlex.quote(str(log_directory))} "
                f"confidence_threshold:={config.confidence_threshold:.6f} "
                f"sigma_threshold_m:={config.sigma_threshold_m:.6f} "
                f"cruise_altitude_m:={config.cruise_altitude_m:.6f}"
            )
            ros_process, handle = self._start_process(
                ["bash", "-lc", ros_command],
                log_path=run_directory / "aeroland.log",
            )
            processes.append(ros_process)
            handles.append(handle)

            deadline = time.monotonic() + self.timeout_seconds
            final_frame: pd.DataFrame | None = None
            while time.monotonic() < deadline:
                if cancel_event.is_set():
                    raise MissionCancelled("Mission cancelled by operator")
                if px4_process.poll() is not None:
                    raise RunnerError(
                        f"PX4/Gazebo stopped unexpectedly; inspect {run_directory / 'px4_gazebo.log'}"
                    )
                if ros_process.poll() is not None:
                    raise RunnerError(
                        f"AeroLand launch stopped unexpectedly; inspect {run_directory / 'aeroland.log'}"
                    )
                if gzweb_process is not None and gzweb_process.poll() is not None:
                    self._gzweb_ready.clear()
                    self._gzweb_problem = (
                        "The optional browser bridge disconnected. The flight mission "
                        "is continuing in the desktop Gazebo window; inspect "
                        f"{run_directory / 'gzweb_bridge.log'}."
                    )
                    gzweb_process = None
                telemetry_path = self._latest_telemetry(log_directory)
                state, frame = self._read_state(telemetry_path)
                if (
                    gzweb_process is not None
                    and frame is not None
                    and not frame.empty
                    and not self._gzweb_ready.is_set()
                ):
                    self._gzweb_ready.set()
                progress(self._progress_for_state(state), state)
                if state == "COMPLETE" and frame is not None:
                    final_frame = frame
                    break
                time.sleep(0.5)

            if final_frame is None:
                raise RunnerError(
                    f"Mission exceeded the {self.timeout_seconds}-second safety timeout"
                )

            time.sleep(0.4)
            telemetry_path = self._latest_telemetry(log_directory)
            _, refreshed_frame = self._read_state(telemetry_path)
            if refreshed_frame is not None:
                final_frame = refreshed_frame

            if gzweb_process is not None and self.gzweb_postflight_seconds > 0:
                progress(0.99, "LANDING COMPLETE · LIVE VIEW")
                view_deadline = (
                    time.monotonic() + self.gzweb_postflight_seconds
                )
                while time.monotonic() < view_deadline:
                    if cancel_event.is_set():
                        break
                    if px4_process.poll() is not None:
                        break
                    if gzweb_process.poll() is not None:
                        self._gzweb_ready.clear()
                        break
                    time.sleep(0.5)

            return mission_result_from_telemetry(
                final_frame,
                config,
                source="gazebo_sitl",
                run_id=run_id,
            )
        finally:
            self._gzweb_ready.clear()
            self._gzweb_client_ready.clear()
            for process in reversed(processes):
                self._terminate(process)
            for handle in handles:
                handle.close()
            self._mission_lock.release()


def runner_from_environment() -> DemoRunner | GazeboRunner:
    """Create the configured runner without accepting mode changes from users."""

    mode = os.getenv("AEROLAND_RUNNER_MODE", "demo").strip().lower()
    if mode == "demo":
        return DemoRunner()
    if mode == "gazebo":
        return GazeboRunner()
    raise RuntimeError("AEROLAND_RUNNER_MODE must be 'demo' or 'gazebo'")
