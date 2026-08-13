"""Generate numerical and graphical reports from AeroLand mission logs."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


STATE_ORDER = [
    "WAITING",
    "PRESTREAM",
    "ACTIVATE",
    "TAKEOFF",
    "INSPECTION",
    "SEARCH",
    "ALIGN",
    "DESCEND",
    "RECOVER",
    "LANDING",
    "COMPLETE",
]

CONFIDENCE_LIMIT = 0.60
SIGMA_LIMIT_METERS = 0.12


def _optional_float(value):
    if value is None or value == "":
        return None
    return float(value)


def _read_records(log_path):
    records = []
    with log_path.open("r", encoding="utf-8", newline="") as log_file:
        for row in csv.DictReader(log_file):
            records.append(
                {
                    "time": float(row["elapsed_seconds"]),
                    "state": row["mission_state"],
                    "x": _optional_float(row["x_m"]),
                    "y": _optional_float(row["y_m"]),
                    "z": _optional_float(row["z_ned_m"]),
                    "altitude": _optional_float(row["altitude_m"]),
                    "detected": row["marker_detected"] == "1",
                    "error_x": _optional_float(
                        row["marker_error_x"]
                    ),
                    "error_y": _optional_float(
                        row["marker_error_y"]
                    ),
                    "error_norm": _optional_float(
                        row["marker_error_norm"]
                    ),
                    "confidence": _optional_float(
                        row.get("landing_confidence")
                    ),
                    "sigma_x": _optional_float(
                        row.get("marker_sigma_x_m")
                    ),
                    "sigma_y": _optional_float(
                        row.get("marker_sigma_y_m")
                    ),
                    "sigma_radial": _optional_float(
                        row.get("marker_sigma_radial_m")
                    ),
                    "safe_to_descend": (
                        row.get("safe_to_descend") == "1"
                        if row.get("safe_to_descend") is not None
                        else None
                    ),
                }
            )
    if not records:
        raise ValueError(f"No data rows found in {log_path}")
    return records


def _latest_log(log_directory):
    candidates = sorted(
        log_directory.glob("aeroland_mission_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No AeroLand mission CSV files found in {log_directory}"
        )
    return candidates[0]


def _first_time(records, state):
    for record in records:
        if record["state"] == state:
            return record["time"]
    return None


def _last_position(records):
    for record in reversed(records):
        if record["x"] is not None and record["y"] is not None:
            return record
    return None


def _count_entries(records, target_state):
    count = 0
    previous_state = None
    for record in records:
        current_state = record["state"]
        if current_state == target_state and previous_state != target_state:
            count += 1
        previous_state = current_state
    return count


def _mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def _count_uncertainty_pauses(records):
    count = 0
    previously_safe = None
    for record in records:
        if record["state"] != "DESCEND":
            continue
        safe = record["safe_to_descend"]
        if safe is None:
            continue
        if previously_safe is True and safe is False:
            count += 1
        previously_safe = safe
    return count


def _format_value(value, precision=3):
    if value is None:
        return "not available"
    return f"{value:.{precision}f}"


def _format_with_unit(value, unit, precision=3):
    if value is None:
        return "not available"
    return f"{value:.{precision}f} {unit}"


def _calculate_metrics(records):
    start_time = records[0]["time"]
    complete_time = _first_time(records, "COMPLETE")
    end_time = complete_time
    if end_time is None:
        end_time = records[-1]["time"]

    active_records = [
        record
        for record in records
        if record["time"] <= end_time
    ]
    altitudes = [
        record["altitude"]
        for record in active_records
        if record["altitude"] is not None
    ]
    descent_errors = [
        record["error_norm"]
        for record in active_records
        if record["state"] == "DESCEND"
        and record["error_norm"] is not None
    ]
    descent_confidences = [
        record["confidence"]
        for record in active_records
        if record["state"] == "DESCEND"
        and record["confidence"] is not None
    ]
    descent_sigmas = [
        record["sigma_radial"]
        for record in active_records
        if record["state"] == "DESCEND"
        and record["sigma_radial"] is not None
    ]
    descent_approvals = [
        record["safe_to_descend"]
        for record in active_records
        if record["state"] == "DESCEND"
        and record["safe_to_descend"] is not None
    ]
    guidance_states = {"SEARCH", "ALIGN", "DESCEND", "RECOVER"}
    guidance_records = [
        record
        for record in active_records
        if record["state"] in guidance_states
    ]
    detected_count = sum(
        1 for record in guidance_records if record["detected"]
    )
    availability = None
    if guidance_records:
        availability = 100.0 * detected_count / len(guidance_records)

    final_position = _last_position(active_records)
    final_horizontal_error = None
    final_altitude = None
    if final_position is not None:
        final_horizontal_error = math.hypot(
            final_position["x"],
            final_position["y"],
        )
        final_altitude = final_position["altitude"]

    return {
        "sample_count": len(active_records),
        "mission_duration": end_time - start_time,
        "completed": complete_time is not None,
        "maximum_altitude": max(altitudes) if altitudes else None,
        "final_horizontal_error": final_horizontal_error,
        "final_altitude": final_altitude,
        "marker_availability": availability,
        "mean_descent_error": _mean(descent_errors),
        "maximum_descent_error": (
            max(descent_errors) if descent_errors else None
        ),
        "mean_descent_confidence": _mean(descent_confidences),
        "minimum_descent_confidence": (
            min(descent_confidences) if descent_confidences else None
        ),
        "mean_descent_sigma": _mean(descent_sigmas),
        "maximum_descent_sigma": (
            max(descent_sigmas) if descent_sigmas else None
        ),
        "descent_approval_rate": (
            100.0 * sum(descent_approvals) / len(descent_approvals)
            if descent_approvals
            else None
        ),
        "uncertainty_pause_count": _count_uncertainty_pauses(
            active_records
        ),
        "recovery_count": _count_entries(
            active_records,
            "RECOVER",
        ),
        "active_records": active_records,
    }


def _summary_lines(log_path, metrics):
    status = "COMPLETE" if metrics["completed"] else "INCOMPLETE"
    return [
        "AeroLand Mission Performance Summary",
        "====================================",
        f"Source log: {log_path}",
        f"Mission status: {status}",
        f"Samples analyzed: {metrics['sample_count']}",
        (
            "Mission duration: "
            f"{_format_value(metrics['mission_duration'])} s"
        ),
        (
            "Maximum altitude: "
            f"{_format_value(metrics['maximum_altitude'])} m"
        ),
        (
            "Final horizontal error: "
            f"{_format_value(metrics['final_horizontal_error'])} m"
        ),
        (
            "Final vehicle-origin altitude: "
            f"{_format_value(metrics['final_altitude'])} m"
        ),
        (
            "Marker availability during guidance: "
            f"{_format_value(metrics['marker_availability'], 1)} %"
        ),
        (
            "Mean marker error during descent: "
            f"{_format_value(metrics['mean_descent_error'])}"
        ),
        (
            "Maximum marker error during descent: "
            f"{_format_value(metrics['maximum_descent_error'])}"
        ),
        (
            "Mean landing confidence during descent: "
            f"{_format_value(metrics['mean_descent_confidence'])}"
        ),
        (
            "Minimum landing confidence during descent: "
            f"{_format_value(metrics['minimum_descent_confidence'])}"
        ),
        (
            "Mean ground-plane sigma during descent: "
            f"{_format_with_unit(metrics['mean_descent_sigma'], 'm')}"
        ),
        (
            "Maximum ground-plane sigma during descent: "
            f"{_format_with_unit(metrics['maximum_descent_sigma'], 'm')}"
        ),
        (
            "Uncertainty-approved descent samples: "
            f"{_format_with_unit(metrics['descent_approval_rate'], '%', 1)}"
        ),
        (
            "Uncertainty pause events: "
            f"{metrics['uncertainty_pause_count']}"
        ),
        f"Recovery events: {metrics['recovery_count']}",
    ]


def _plot_trajectory(axis, records):
    positions = [
        record
        for record in records
        if record["x"] is not None and record["y"] is not None
    ]
    east = [record["y"] for record in positions]
    north = [record["x"] for record in positions]
    axis.plot(east, north, color="#1565c0", linewidth=1.6)
    if positions:
        axis.scatter(
            east[0],
            north[0],
            color="#2e7d32",
            label="Start",
            zorder=3,
        )
        axis.scatter(
            east[-1],
            north[-1],
            color="#c62828",
            label="Landing",
            zorder=3,
        )
    axis.set_title("Horizontal trajectory")
    axis.set_xlabel("East, y (m)")
    axis.set_ylabel("North, x (m)")
    axis.axis("equal")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="best")


def _plot_altitude(axis, records):
    altitude_records = [
        record
        for record in records
        if record["altitude"] is not None
    ]
    times = [record["time"] for record in altitude_records]
    altitudes = [record["altitude"] for record in altitude_records]
    axis.plot(times, altitudes, color="#6a1b9a", linewidth=1.6)
    axis.fill_between(times, altitudes, alpha=0.15, color="#6a1b9a")
    axis.set_title("Altitude profile")
    axis.set_xlabel("Elapsed time (s)")
    axis.set_ylabel("Altitude (m)")
    axis.grid(True, alpha=0.3)


def _plot_marker_error(axis, records):
    error_records = [
        record
        for record in records
        if record["error_norm"] is not None
    ]
    times = [record["time"] for record in error_records]
    errors = [record["error_norm"] for record in error_records]
    axis.plot(times, errors, color="#ef6c00", linewidth=1.3)
    axis.axhline(
        0.08,
        color="#c62828",
        linestyle="--",
        linewidth=1.0,
        label="Alignment tolerance",
    )
    axis.set_title("ArUco centering error")
    axis.set_xlabel("Elapsed time (s)")
    axis.set_ylabel("Normalized image error")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="best")


def _plot_states(axis, records):
    states_present = [
        state
        for state in STATE_ORDER
        if any(record["state"] == state for record in records)
    ]
    extra_states = sorted(
        {
            record["state"]
            for record in records
            if record["state"] not in states_present
        }
    )
    states = states_present + extra_states
    state_index = {
        state: index for index, state in enumerate(states)
    }
    times = [record["time"] for record in records]
    values = [state_index[record["state"]] for record in records]
    axis.step(times, values, where="post", color="#00838f")
    axis.set_yticks(range(len(states)))
    axis.set_yticklabels(states)
    axis.set_title("Mission state timeline")
    axis.set_xlabel("Elapsed time (s)")
    axis.grid(True, axis="x", alpha=0.3)


def _plot_confidence(axis, records):
    confidence_records = [
        record
        for record in records
        if record["confidence"] is not None
    ]
    times = [record["time"] for record in confidence_records]
    confidence = [
        record["confidence"] for record in confidence_records
    ]
    approved = [
        float(bool(record["safe_to_descend"]))
        for record in confidence_records
    ]
    axis.plot(
        times,
        confidence,
        color="#1565c0",
        linewidth=1.5,
        label="Confidence",
    )
    axis.step(
        times,
        approved,
        where="post",
        color="#2e7d32",
        linewidth=1.1,
        alpha=0.8,
        label="Safe to descend",
    )
    axis.axhline(
        CONFIDENCE_LIMIT,
        color="#c62828",
        linestyle="--",
        linewidth=1.0,
        label="Confidence threshold",
    )
    axis.set_ylim(-0.05, 1.05)
    axis.set_title("Landing confidence and descent approval")
    axis.set_xlabel("Elapsed time (s)")
    axis.set_ylabel("Score / approval")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="best")


def _plot_sigma(axis, records):
    sigma_records = [
        record
        for record in records
        if record["sigma_radial"] is not None
    ]
    times = [record["time"] for record in sigma_records]
    radial = [record["sigma_radial"] for record in sigma_records]
    sigma_x = [record["sigma_x"] for record in sigma_records]
    sigma_y = [record["sigma_y"] for record in sigma_records]
    axis.plot(
        times,
        radial,
        color="#6a1b9a",
        linewidth=1.5,
        label="Radial sigma",
    )
    axis.plot(
        times,
        sigma_x,
        color="#00838f",
        linewidth=1.0,
        alpha=0.8,
        label="Sigma x",
    )
    axis.plot(
        times,
        sigma_y,
        color="#ef6c00",
        linewidth=1.0,
        alpha=0.8,
        label="Sigma y",
    )
    axis.axhline(
        SIGMA_LIMIT_METERS,
        color="#c62828",
        linestyle="--",
        linewidth=1.0,
        label="Sigma threshold",
    )
    axis.set_title("Ground-plane landing uncertainty")
    axis.set_xlabel("Elapsed time (s)")
    axis.set_ylabel("Standard deviation (m)")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="best")


def _write_plot(output_path, records):
    figure, axes = plt.subplots(3, 2, figsize=(13, 13))
    _plot_trajectory(axes[0, 0], records)
    _plot_altitude(axes[0, 1], records)
    _plot_marker_error(axes[1, 0], records)
    _plot_confidence(axes[1, 1], records)
    _plot_sigma(axes[2, 0], records)
    _plot_states(axes[2, 1], records)
    figure.suptitle("AeroLand Integrated Mission Report", fontsize=15)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def _parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate an AeroLand mission report."
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        type=Path,
        help="Mission CSV file; defaults to the newest mission log.",
    )
    parser.add_argument(
        "--log-directory",
        type=Path,
        default=Path("~/aeroland_ws/mission_logs"),
        help="Directory searched when no CSV path is supplied.",
    )
    return parser.parse_args()


def main():
    """Generate summary text and plots for an AeroLand mission."""
    arguments = _parse_arguments()
    log_directory = arguments.log_directory.expanduser()
    log_path = arguments.log_file
    if log_path is None:
        log_path = _latest_log(log_directory)
    else:
        log_path = log_path.expanduser().resolve()

    records = _read_records(log_path)
    metrics = _calculate_metrics(records)
    summary = _summary_lines(log_path, metrics)

    summary_path = log_path.with_name(
        f"{log_path.stem}_summary.txt"
    )
    plot_path = log_path.with_name(f"{log_path.stem}_report.png")
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")
    _write_plot(plot_path, metrics["active_records"])

    print("\n".join(summary))
    print(f"Summary file: {summary_path}")
    print(f"Plot file: {plot_path}")


if __name__ == "__main__":
    main()
