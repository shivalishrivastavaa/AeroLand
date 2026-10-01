"""Contract tests for the local AeroLand mission API."""

from io import StringIO
import time

import pandas as pd
import pytest
from pydantic import ValidationError

from backend.main import create_mission, health, mission_status, mission_telemetry
from backend.models import MissionRequest


def test_health_reports_honest_demo_capabilities():
    response = health()

    assert response.model_dump() == {
        "status": "ok",
        "runner": "demo",
        "detail": "Mission API is ready in synthetic integration-test mode.",
        "supports_wind": True,
        "supports_seed": True,
    }


def test_mission_completes_and_returns_contract_telemetry():
    response = create_mission(
        MissionRequest(
            confidence_threshold=0.60,
            sigma_threshold_m=0.12,
            cruise_altitude_m=2.50,
            wind_speed_mps=1.0,
            random_seed=17,
        )
    )
    run_id = response.run_id

    deadline = time.monotonic() + 5
    status = response
    while time.monotonic() < deadline and status.status not in {
        "complete",
        "failed",
    }:
        time.sleep(0.03)
        status = mission_status(run_id)

    assert status.status == "complete"
    assert status.runner == "demo"
    assert status.result["sample_count"] > 100

    telemetry_response = mission_telemetry(run_id)
    frame = pd.read_csv(StringIO(telemetry_response.body.decode("utf-8")))
    assert frame.iloc[-1]["mission_state"] in {"COMPLETE", "ABORTED"}
    assert "marker_sigma_radial_m" in frame


def test_api_rejects_out_of_envelope_values():
    with pytest.raises(ValidationError):
        MissionRequest(cruise_altitude_m=12.0)
