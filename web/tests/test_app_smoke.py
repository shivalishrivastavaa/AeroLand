"""Streamlit smoke tests for the guided mission-control interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def _widget_by_label(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def test_app_renders_guide_and_runs_crosswind_preset():
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["FLIGHT DATA", "RESULTS", "SYSTEM"]
    assert _widget_by_label(app.expander, "HOW TO USE AEROLAND")
    assert _widget_by_label(app.button, "Run mission")

    preset = _widget_by_label(app.selectbox, "Mission preset")
    preset.set_value("Crosswind evaluation")
    app.run(timeout=45)

    assert _widget_by_label(app.slider, "Wind disturbance (m/s)").value == 2.0
    assert _widget_by_label(app.slider, "Minimum landing confidence").value == 0.60
    assert _widget_by_label(app.slider, "Maximum radial sigma (m)").value == 0.12

    _widget_by_label(app.button, "Run mission").click()
    app.run(timeout=45)

    assert not app.exception
    result = app.session_state["mission_result"]
    assert result.configuration.wind_speed_mps == 2.0
    assert result.configuration.confidence_threshold == 0.60
    assert len(app.get("download_button")) == 4
