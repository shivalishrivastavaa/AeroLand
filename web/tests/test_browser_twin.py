from aeroland_web.browser_twin import browser_twin_html
from aeroland_web.simulation import MissionConfig, run_mission


def _mission_frame():
    return run_mission(
        MissionConfig(
            confidence_threshold=0.60,
            sigma_threshold_m=0.12,
            cruise_altitude_m=2.50,
            wind_speed_mps=2.00,
            random_seed=7,
        )
    ).telemetry


def test_browser_twin_embeds_mission_telemetry_and_animation_controls():
    page = browser_twin_html(_mission_frame())

    assert '<canvas id="scene"' in page
    assert "requestAnimationFrame(tick)" in page
    assert 'id="play"' in page
    assert 'id="timeline"' in page
    assert '"mission_state"' in page
    assert "NaN" not in page


def test_browser_twin_has_visible_drone_parts_and_operator_readouts():
    page = browser_twin_html(_mission_frame())

    assert "function drawDrone" in page
    assert "DESCENT GATE" in page
    assert "RADIAL σ" in page
    assert "DRAG TO ORBIT" in page
