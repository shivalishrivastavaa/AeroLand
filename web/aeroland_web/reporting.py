"""Mission summaries and downloadable result bundles."""

from __future__ import annotations

from io import BytesIO
import json
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .simulation import MissionResult, STATE_ORDER


def summary_text(result: MissionResult) -> str:
    """Create the portable plain-text mission summary."""

    metrics = result.metrics
    source_labels = {
        "browser_digital_twin": "Browser digital-twin demonstrator (synthetic telemetry)",
        "backend_demo": "Mission API integration test (synthetic telemetry)",
        "gazebo_sitl": "PX4 SITL + Gazebo (simulation telemetry)",
    }
    model_label = source_labels.get(result.source, result.source)
    lines = [
            "AeroLand Mission Performance Summary",
            "====================================",
            f"Model: {model_label}",
            f"Run ID: {result.run_id or 'local-browser-run'}",
            f"Mission: {result.configuration.mission_name}",
            f"Mission status: {metrics['mission_status']}",
            f"Mission duration: {metrics['mission_duration_s']:.1f} s",
            f"Maximum altitude: {metrics['maximum_altitude_m']:.3f} m",
            f"Final horizontal error: {metrics['final_horizontal_error_m']:.3f} m",
            f"Mean landing confidence: {metrics['mean_landing_confidence']:.3f}",
            f"Minimum landing confidence: {metrics['minimum_landing_confidence']:.3f}",
            f"Mean ground-plane sigma: {metrics['mean_ground_sigma_m']:.3f} m",
            f"Maximum ground-plane sigma: {metrics['maximum_ground_sigma_m']:.3f} m",
            f"Uncertainty-approved descent samples: {metrics['descent_approval_pct']:.1f} %",
            f"Uncertainty pause events: {metrics['uncertainty_pause_events']}",
            f"Recovery events: {metrics['recovery_events']}",
            f"Confidence threshold: {metrics['confidence_threshold']:.2f}",
            f"Sigma threshold: {metrics['sigma_threshold_m']:.3f} m",
            f"Wind disturbance: {metrics['wind_speed_mps']:.2f} m/s",
        ]
    if result.source == "gazebo_sitl":
        lines.extend(
            [
                "",
                "This result was generated in PX4 SITL and Gazebo simulation.",
                "It must not be represented as physical-flight validation.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "This result contains synthetic telemetry and must not be",
                "represented as PX4/Gazebo or physical-flight validation.",
            ]
        )
    return "\n".join(lines)


def event_log(frame: pd.DataFrame) -> pd.DataFrame:
    """Return state transitions and descent-gate changes."""

    events: list[dict] = []
    previous_state = None
    previous_gate = False
    for row in frame.itertuples(index=False):
        state = str(row.mission_state)
        gate = bool(row.safe_to_descend)
        if state != previous_state:
            events.append(
                {
                    "T+": f"{row.elapsed_seconds:05.1f}s",
                    "Event": "STATE",
                    "Status": state,
                    "Detail": f"Altitude {row.altitude_m:.2f} m",
                }
            )
            previous_state = state
        if gate != previous_gate and state == "DESCEND":
            events.append(
                {
                    "T+": f"{row.elapsed_seconds:05.1f}s",
                    "Event": "DESCENT GATE",
                    "Status": "APPROVED" if gate else "PAUSED",
                    "Detail": (
                        f"confidence {row.landing_confidence:.2f} · "
                        f"sigma {row.marker_sigma_radial_m:.3f} m"
                    ),
                }
            )
        previous_gate = gate
    return pd.DataFrame(events)


def render_report_png(result: MissionResult) -> bytes:
    """Render a portable high-resolution four-panel technical report."""

    frame = result.telemetry
    config = result.configuration
    state_to_index = {state: index for index, state in enumerate(STATE_ORDER)}
    state_values = [state_to_index.get(state, -1) for state in frame["mission_state"]]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "text.color": "#EDF7FB",
            "axes.labelcolor": "#A49F95",
            "xtick.color": "#858178",
            "ytick.color": "#858178",
            "axes.edgecolor": "#1D3442",
            "axes.titlecolor": "#EDF7FB",
        }
    )
    figure, axes = plt.subplots(2, 2, figsize=(15.5, 8.4), dpi=170)
    figure.patch.set_facecolor("#000205")
    for axis in axes.flat:
        axis.set_facecolor("#05090E")
        axis.grid(color="#223846", alpha=0.38, linewidth=0.55)
        axis.spines[["top", "right"]].set_visible(False)

    time_values = frame["elapsed_seconds"]
    axes[0, 0].plot(time_values, frame["altitude_m"], color="#C8A7FF", linewidth=1.8)
    axes[0, 0].fill_between(time_values, frame["altitude_m"], color="#C8A7FF", alpha=0.16)
    axes[0, 0].set_title("ALTITUDE PROFILE", loc="left", fontsize=9.5, fontweight="bold")
    axes[0, 0].set_ylabel("ALTITUDE / m")

    axes[0, 1].plot(
        time_values,
        frame["landing_confidence"],
        color="#F3F0E8",
        linewidth=1.6,
        label="confidence",
    )
    axes[0, 1].step(
        time_values,
        frame["safe_to_descend"],
        color="#F0B95A",
        linewidth=1.4,
        where="post",
        label="descent gate",
    )
    axes[0, 1].axhline(config.confidence_threshold, color="#FF6078", linestyle="--", linewidth=1.1)
    axes[0, 1].set_ylim(-0.04, 1.05)
    axes[0, 1].set_title("LANDING CONFIDENCE + DESCENT GATE", loc="left", fontsize=9.5, fontweight="bold")
    axes[0, 1].legend(frameon=False, labelcolor="#A49F95", fontsize=7.5, loc="upper left")

    axes[1, 0].plot(
        time_values,
        frame["marker_sigma_radial_m"],
        color="#C8A7FF",
        linewidth=1.7,
        label="radial σ",
    )
    axes[1, 0].plot(time_values, frame["marker_sigma_x_m"], color="#F3F0E8", linewidth=1.1, label="σx")
    axes[1, 0].plot(time_values, frame["marker_sigma_y_m"], color="#6FDC9B", linewidth=1.1, label="σy")
    axes[1, 0].axhline(config.sigma_threshold_m, color="#FF6078", linestyle="--", linewidth=1.1)
    axes[1, 0].set_title("GROUND-PLANE UNCERTAINTY", loc="left", fontsize=9.5, fontweight="bold")
    axes[1, 0].set_ylabel("STANDARD DEVIATION / m")
    axes[1, 0].legend(frameon=False, labelcolor="#A49F95", fontsize=7.5, loc="upper left")

    axes[1, 1].step(time_values, state_values, where="post", color="#F0B95A", linewidth=1.8)
    used_states = [state for state in STATE_ORDER if state in set(frame["mission_state"])]
    axes[1, 1].set_yticks([state_to_index[state] for state in used_states], labels=used_states)
    axes[1, 1].set_title("MISSION-STATE SEQUENCE", loc="left", fontsize=9.5, fontweight="bold")

    for axis in axes.flat:
        axis.set_xlabel("ELAPSED TIME / s")

    status = result.metrics["mission_status"]
    source_labels = {
        "browser_digital_twin": "BROWSER DIGITAL TWIN",
        "backend_demo": "BACKEND INTEGRATION TEST",
        "gazebo_sitl": "PX4 SITL + GAZEBO",
    }
    subtitle = (
        f"{source_labels.get(result.source, result.source.upper())} · {status} · "
        f"WIND {config.wind_speed_mps:.1f} m/s · "
        f"CONF ≥ {config.confidence_threshold:.2f} · σ ≤ {config.sigma_threshold_m:.3f} m"
    )
    figure.suptitle(
        "AEROLAND  /  MISSION ANALYSIS REPORT",
        x=0.055,
        y=0.986,
        ha="left",
        fontsize=15,
        fontweight="bold",
        color="#E8F7FA",
    )
    figure.text(0.055, 0.948, subtitle, color="#F0B95A", fontsize=8.5)
    figure.subplots_adjust(left=0.07, right=0.975, bottom=0.075, top=0.895, hspace=0.34, wspace=0.21)

    buffer = BytesIO()
    figure.savefig(buffer, format="png", facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def result_bundle(result: MissionResult) -> bytes:
    """Build a self-contained ZIP containing data, configuration, and report."""

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("telemetry.csv", result.telemetry.to_csv(index=False))
        archive.writestr("summary.txt", summary_text(result))
        archive.writestr(
            "configuration.json",
            json.dumps(result.configuration.to_dict(), indent=2, sort_keys=True),
        )
        archive.writestr("event_log.csv", event_log(result.telemetry).to_csv(index=False))
        archive.writestr("mission_report.png", render_report_png(result))
        archive.writestr(
            "README.txt",
            (
                "AeroLand PX4 SITL + Gazebo simulation result bundle.\n"
                "Simulation evidence only; this is not physical-flight validation.\n"
                if result.source == "gazebo_sitl"
                else "AeroLand demonstrator result bundle.\n"
                "Synthetic telemetry only; this is not PX4/Gazebo flight evidence.\n"
            ),
        )
    return buffer.getvalue()
