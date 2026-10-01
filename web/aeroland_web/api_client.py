"""Client for the optional local AeroLand mission service."""

from __future__ import annotations

from io import BytesIO
import time
from typing import Callable

import pandas as pd
import requests

from .simulation import MissionConfig, MissionResult, mission_result_from_telemetry


class MissionAPIError(RuntimeError):
    """Raised when the mission service is unavailable or a run fails."""


def backend_health(base_url: str, timeout_seconds: float = 1.5) -> dict:
    """Return normalized backend health without leaking request exceptions."""

    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("health response was not an object")
        return payload
    except (requests.RequestException, ValueError) as error:
        return {
            "status": "not_ready",
            "runner": "unknown",
            "detail": f"Mission service is unreachable: {error}",
            "supports_wind": False,
            "supports_seed": False,
        }


def run_remote_mission(
    base_url: str,
    config: MissionConfig,
    *,
    timeout_seconds: float = 240.0,
    progress_callback: Callable[[float, str], None] | None = None,
) -> MissionResult:
    """Start one validated mission, poll its state, and retrieve telemetry."""

    endpoint = base_url.rstrip("/")
    try:
        response = requests.post(
            f"{endpoint}/v1/missions",
            json=config.to_dict(),
            timeout=10,
        )
        response.raise_for_status()
        mission = response.json()
        run_id = str(mission["run_id"])
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        raise MissionAPIError(f"Could not start the mission: {error}") from error

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            status_response = requests.get(
                f"{endpoint}/v1/missions/{run_id}",
                timeout=10,
            )
            status_response.raise_for_status()
            status = status_response.json()
        except (requests.RequestException, ValueError) as error:
            raise MissionAPIError(f"Lost connection to mission {run_id}: {error}") from error

        if progress_callback:
            progress_callback(
                float(status.get("progress", 0.0)),
                str(status.get("current_state", "RUNNING")),
            )
        if status.get("status") == "complete":
            try:
                telemetry_response = requests.get(
                    f"{endpoint}/v1/missions/{run_id}/telemetry",
                    timeout=30,
                )
                telemetry_response.raise_for_status()
                frame = pd.read_csv(BytesIO(telemetry_response.content))
                runner = str(status.get("runner", "demo"))
                source = "gazebo_sitl" if runner == "gazebo" else "backend_demo"
                return mission_result_from_telemetry(
                    frame,
                    config,
                    source=source,
                    run_id=run_id,
                )
            except (requests.RequestException, ValueError, pd.errors.ParserError) as error:
                raise MissionAPIError(f"Mission telemetry could not be loaded: {error}") from error
        if status.get("status") in {"failed", "cancelled"}:
            message = status.get("error") or f"Mission {status.get('status')}"
            raise MissionAPIError(str(message))
        time.sleep(0.5)

    try:
        requests.delete(f"{endpoint}/v1/missions/{run_id}", timeout=5)
    except requests.RequestException:
        pass
    raise MissionAPIError(f"Mission {run_id} exceeded the {timeout_seconds:.0f}-second client timeout")
