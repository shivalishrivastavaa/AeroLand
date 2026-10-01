"""Regression tests for the browser mission model and result bundle."""

from io import BytesIO
import zipfile

import pandas as pd

from aeroland_web.reporting import result_bundle, summary_text
from aeroland_web.simulation import MissionConfig, run_mission


def test_default_mission_completes_and_respects_schema():
    result = run_mission(MissionConfig())

    assert result.metrics["mission_status"] == "COMPLETE"
    assert result.metrics["sample_count"] == len(result.telemetry)
    assert result.metrics["maximum_altitude_m"] >= 2.49
    assert result.telemetry.columns.tolist() == [
        "elapsed_seconds",
        "mission_state",
        "x_m",
        "y_m",
        "z_ned_m",
        "altitude_m",
        "marker_detected",
        "marker_error_x",
        "marker_error_y",
        "marker_error_norm",
        "landing_confidence",
        "marker_sigma_x_m",
        "marker_sigma_y_m",
        "marker_sigma_radial_m",
        "safe_to_descend",
    ]


def test_same_seed_and_configuration_are_reproducible():
    config = MissionConfig(wind_speed_mps=2.0, random_seed=17)
    first = run_mission(config)
    second = run_mission(config)

    pd.testing.assert_frame_equal(first.telemetry, second.telemetry)
    assert first.metrics == second.metrics


def test_wind_changes_perception_uncertainty_and_landing():
    calm = run_mission(MissionConfig(wind_speed_mps=0.0, random_seed=7))
    windy = run_mission(MissionConfig(wind_speed_mps=2.0, random_seed=7))

    assert windy.metrics["mean_ground_sigma_m"] > calm.metrics["mean_ground_sigma_m"]
    assert windy.metrics["mean_landing_confidence"] < calm.metrics["mean_landing_confidence"]
    assert windy.metrics["final_horizontal_error_m"] != calm.metrics["final_horizontal_error_m"]
    assert not windy.telemetry["marker_error_norm"].equals(calm.telemetry["marker_error_norm"])


def test_stricter_envelope_reduces_approval_or_prevents_completion():
    baseline = run_mission(MissionConfig(random_seed=7))
    strict = run_mission(
        MissionConfig(
            confidence_threshold=0.75,
            sigma_threshold_m=0.08,
            wind_speed_mps=2.0,
            random_seed=7,
        )
    )

    assert (
        strict.metrics["descent_approval_pct"] < baseline.metrics["descent_approval_pct"]
        or strict.metrics["mission_status"] == "ABORTED"
    )


def test_bundle_contains_portable_report_products():
    result = run_mission(MissionConfig())
    bundle = result_bundle(result)

    with zipfile.ZipFile(BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {
            "README.txt",
            "configuration.json",
            "event_log.csv",
            "mission_report.png",
            "summary.txt",
            "telemetry.csv",
        }
        assert archive.getinfo("mission_report.png").file_size > 20_000
        assert "synthetic" in archive.read("summary.txt").decode("utf-8").lower()

    assert "must not" in summary_text(result)
