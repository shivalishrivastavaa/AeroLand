"""Deterministic browser-side mission model for the AeroLand web console.

This is intentionally described as a digital-twin *demonstrator*. It mirrors
the AeroLand state machine and uncertainty gate, but it is not PX4 or Gazebo.
The live backend can implement the same data contract later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd


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
    "ABORTED",
]


@dataclass(frozen=True)
class MissionConfig:
    """User-adjustable inputs for one deterministic browser mission."""

    confidence_threshold: float = 0.60
    sigma_threshold_m: float = 0.12
    cruise_altitude_m: float = 2.50
    wind_speed_mps: float = 0.0
    random_seed: int = 7
    mission_name: str = "Inspection + precision landing"

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""

        return asdict(self)


@dataclass
class MissionResult:
    """Telemetry and derived metrics returned by a mission runner."""

    telemetry: pd.DataFrame
    metrics: dict
    configuration: MissionConfig
    source: str = "browser_digital_twin"
    run_id: str | None = None


def _interpolate_waypoints(progress: float, altitude: float) -> tuple[float, float, float]:
    """Interpolate a compact four-leg inspection route."""

    points = np.array(
        [
            [0.00, 0.00],
            [1.40, 0.25],
            [1.35, 1.35],
            [0.20, 1.25],
            [0.00, 0.00],
        ]
    )
    scaled = min(max(progress, 0.0), 0.999999) * (len(points) - 1)
    index = int(scaled)
    fraction = scaled - index
    xy = points[index] * (1.0 - fraction) + points[index + 1] * fraction
    return float(xy[0]), float(xy[1]), altitude


def _calculate_metrics(frame: pd.DataFrame, config: MissionConfig) -> dict:
    """Calculate user-facing mission metrics from generated telemetry."""

    guidance = frame[frame["mission_state"].isin(["ALIGN", "DESCEND", "RECOVER"])]
    descent = frame[frame["mission_state"] == "DESCEND"]
    detected_mask = guidance["marker_detected"].astype(bool)
    confidence = guidance.loc[detected_mask, "landing_confidence"]
    sigma = guidance.loc[detected_mask, "marker_sigma_radial_m"]
    safe = descent["safe_to_descend"].astype(bool)

    pause_events = int(((safe.shift(1) == True) & (safe == False)).sum())  # noqa: E712
    recoveries = int(
        (
            (frame["mission_state"] == "RECOVER")
            & (frame["mission_state"].shift(1) != "RECOVER")
        ).sum()
    )
    last = frame.iloc[-1]
    completed = str(last["mission_state"]) == "COMPLETE"

    return {
        "mission_status": "COMPLETE" if completed else "ABORTED",
        "mission_duration_s": float(last["elapsed_seconds"]),
        "maximum_altitude_m": float(frame["altitude_m"].max()),
        "final_horizontal_error_m": float(math.hypot(last["x_m"], last["y_m"])),
        "mean_landing_confidence": float(confidence.mean()) if not confidence.empty else 0.0,
        "minimum_landing_confidence": float(confidence.min()) if not confidence.empty else 0.0,
        "mean_ground_sigma_m": float(sigma.mean()) if not sigma.empty else 0.0,
        "maximum_ground_sigma_m": float(sigma.max()) if not sigma.empty else 0.0,
        "descent_approval_pct": float(100.0 * safe.mean()) if not safe.empty else 0.0,
        "uncertainty_pause_events": pause_events,
        "recovery_events": recoveries,
        "confidence_threshold": config.confidence_threshold,
        "sigma_threshold_m": config.sigma_threshold_m,
        "wind_speed_mps": config.wind_speed_mps,
        "sample_count": int(len(frame)),
    }


def mission_result_from_telemetry(
    frame: pd.DataFrame,
    config: MissionConfig,
    *,
    source: str,
    run_id: str | None = None,
) -> MissionResult:
    """Validate runner telemetry and convert it into a display-ready result."""

    required_columns = {
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
    }
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"Telemetry is missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Telemetry contains no samples")

    normalized = frame.copy()
    normalized["mission_state"] = normalized["mission_state"].fillna("UNKNOWN").astype(str)
    for column in required_columns.difference({"mission_state"}):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["marker_detected"] = normalized["marker_detected"].fillna(0).astype(int)
    normalized["safe_to_descend"] = normalized["safe_to_descend"].fillna(0).astype(int)
    normalized = normalized.sort_values("elapsed_seconds").reset_index(drop=True)

    metrics = _calculate_metrics(normalized, config)
    return MissionResult(
        telemetry=normalized,
        metrics=metrics,
        configuration=config,
        source=source,
        run_id=run_id,
    )


def run_mission(config: MissionConfig) -> MissionResult:
    """Run a deterministic uncertainty-gated inspection and landing mission.

    Wind affects vehicle drift, marker-centering error, measurement dispersion,
    detection availability, descent time, and final landing accuracy. The same
    seed and configuration always produce the same telemetry.
    """

    rng = np.random.default_rng(config.random_seed)
    dt = 0.1
    max_time = 82.0
    wind_angle = rng.uniform(0.0, 2.0 * math.pi)
    wind_vector = np.array([math.cos(wind_angle), math.sin(wind_angle)])
    gust_phase = rng.uniform(0.0, 2.0 * math.pi)
    spike_centers = np.array([8.0, 13.0, 16.3]) + rng.normal(0.0, 0.18, 3)

    rows: list[dict] = []
    altitude = 0.0
    position = np.array([0.0, 0.0], dtype=float)
    landing_start = None
    complete_start = None
    safe_streak = 0
    unsafe_streak = 0
    recover_until = -1.0
    align_ready = False

    time_value = 0.0
    while time_value <= max_time + 1e-9:
        detected = False
        marker_error_x = math.nan
        marker_error_y = math.nan
        marker_error_norm = math.nan
        confidence = 0.0
        sigma_x = math.nan
        sigma_y = math.nan
        sigma_radial = math.nan
        safe_to_descend = False

        if time_value < 2.0:
            state = "WAITING"
            position += rng.normal(0.0, 0.0007, 2)
        elif time_value < 4.0:
            state = "PRESTREAM"
            position *= 0.92
        elif time_value < 5.2:
            state = "ACTIVATE"
            position *= 0.94
        elif time_value < 11.2:
            state = "TAKEOFF"
            takeoff_progress = (time_value - 5.2) / 6.0
            altitude = config.cruise_altitude_m * min(max(takeoff_progress, 0.0), 1.0)
            position += rng.normal(0.0, 0.0012 + config.wind_speed_mps * 0.00015, 2)
        elif time_value < 25.0:
            state = "INSPECTION"
            progress = (time_value - 11.2) / 13.8
            route_x, route_y, altitude = _interpolate_waypoints(
                progress,
                config.cruise_altitude_m,
            )
            position = np.array([route_x, route_y])
            position += wind_vector * config.wind_speed_mps * 0.004
            position += rng.normal(0.0, 0.002 + config.wind_speed_mps * 0.0005, 2)
        else:
            guidance_time = time_value - 25.0
            gust = (
                math.sin(guidance_time * 1.35 + gust_phase)
                + 0.45 * math.sin(guidance_time * 3.7 + gust_phase / 2.0)
            )
            process_noise = 0.0025 + 0.0014 * config.wind_speed_mps
            controller_gain = 0.72 if altitude > 0.35 else 1.10
            wind_bias = wind_vector * config.wind_speed_mps * (0.007 + 0.002 * abs(gust))
            position += (
                -controller_gain * position + wind_bias
            ) * dt + rng.normal(0.0, process_noise * math.sqrt(dt), 2)

            # The browser model intentionally degrades perception as wind rises.
            scheduled_dropout = any(
                abs(guidance_time - center) < 0.22 + 0.025 * config.wind_speed_mps
                for center in spike_centers
            )
            random_dropout = rng.random() < min(0.002 + 0.006 * config.wind_speed_mps, 0.08)
            detected = not (scheduled_dropout or random_dropout)

            altitude_scale = max(altitude, 0.28)
            camera_noise = 0.006 + 0.0032 * config.wind_speed_mps
            marker_error_x = float(position[0] / (1.12 * altitude_scale))
            marker_error_y = float(position[1] / (0.86 * altitude_scale))
            marker_error_x += float(rng.normal(0.0, camera_noise))
            marker_error_y += float(rng.normal(0.0, camera_noise))
            marker_error_norm = float(math.hypot(marker_error_x, marker_error_y))

            settling = 0.085 * math.exp(-max(guidance_time - 1.2, 0.0) / 5.0)
            wind_floor = 0.018 + 0.0105 * config.wind_speed_mps
            gust_sigma = 0.007 * config.wind_speed_mps * abs(gust)
            spike_sigma = sum(
                (0.070 + 0.004 * config.wind_speed_mps)
                * math.exp(-0.5 * ((guidance_time - center) / 0.20) ** 2)
                for center in spike_centers
            )
            sigma_radial = wind_floor + settling + gust_sigma + spike_sigma
            sigma_radial += float(rng.normal(0.0, 0.0018))
            sigma_radial = max(sigma_radial, 0.004)
            split = 0.52 + 0.06 * math.sin(guidance_time * 0.7)
            sigma_x = sigma_radial * split
            sigma_y = math.sqrt(max(sigma_radial**2 - sigma_x**2, 0.0))

            center_quality = math.exp(-0.5 * (marker_error_norm / 0.12) ** 2)
            sigma_quality = math.exp(-0.5 * (sigma_radial / 0.12) ** 2)
            wind_quality = math.exp(-0.018 * config.wind_speed_mps**2)
            confidence = center_quality * sigma_quality * wind_quality
            if not detected:
                confidence *= 0.35
            confidence = float(min(max(confidence, 0.0), 1.0))

            guidance_ok = (
                detected
                and marker_error_norm <= 0.12
                and confidence >= config.confidence_threshold
                and sigma_radial <= config.sigma_threshold_m
            )

            if guidance_time < 1.5:
                state = "SEARCH"
                safe_streak = 0
            elif time_value < recover_until:
                state = "RECOVER"
                altitude = min(altitude + 0.05 * dt, config.cruise_altitude_m)
            elif landing_start is None:
                if guidance_ok:
                    safe_streak += 1
                    unsafe_streak = 0
                else:
                    safe_streak = 0
                    unsafe_streak += 1

                if not align_ready:
                    state = "ALIGN"
                    if safe_streak >= 6:
                        align_ready = True
                        unsafe_streak = 0
                else:
                    state = "DESCEND"
                    safe_to_descend = bool(guidance_ok)
                    if safe_to_descend:
                        descent_rate = max(0.15, 0.25 - 0.008 * config.wind_speed_mps)
                        altitude = max(0.12, altitude - descent_rate * dt)
                    if unsafe_streak >= 13:
                        recover_until = time_value + 0.9
                        align_ready = False
                        safe_streak = 0
                        unsafe_streak = 0
                        state = "RECOVER"
                        safe_to_descend = False

                    if altitude <= 0.1201:
                        landing_start = time_value
                        state = "LANDING"
                        safe_to_descend = False
            elif complete_start is None:
                state = "LANDING"
                landing_elapsed = time_value - landing_start
                altitude = max(0.03, 0.12 - 0.06 * landing_elapsed)
                position *= 0.91
                position += wind_vector * config.wind_speed_mps * 0.00045
                if landing_elapsed >= 1.55:
                    complete_start = time_value
                    state = "COMPLETE"
            else:
                state = "COMPLETE"
                altitude = 0.03
                if time_value - complete_start >= 0.7:
                    rows.append(
                        _row(
                            time_value,
                            state,
                            position,
                            altitude,
                            detected,
                            marker_error_x,
                            marker_error_y,
                            marker_error_norm,
                            confidence,
                            sigma_x,
                            sigma_y,
                            sigma_radial,
                            False,
                        )
                    )
                    break

            # Approval is only meaningful after alignment has entered descent.
            if state != "DESCEND":
                safe_to_descend = False
        rows.append(
            _row(
                time_value,
                state,
                position,
                altitude,
                detected,
                marker_error_x,
                marker_error_y,
                marker_error_norm,
                confidence,
                sigma_x,
                sigma_y,
                sigma_radial,
                safe_to_descend,
            )
        )
        time_value = round(time_value + dt, 10)

    if rows[-1]["mission_state"] != "COMPLETE":
        rows[-1]["mission_state"] = "ABORTED"
        rows[-1]["safe_to_descend"] = 0

    frame = pd.DataFrame(rows)
    metrics = _calculate_metrics(frame, config)
    return MissionResult(frame, metrics, config)


def _row(
    time_value: float,
    state: str,
    position: np.ndarray,
    altitude: float,
    detected: bool,
    error_x: float,
    error_y: float,
    error_norm: float,
    confidence: float,
    sigma_x: float,
    sigma_y: float,
    sigma_radial: float,
    safe: bool,
) -> dict:
    """Create one telemetry row using the PX4/Gazebo log contract."""

    return {
        "elapsed_seconds": round(float(time_value), 3),
        "mission_state": state,
        "x_m": float(position[0]),
        "y_m": float(position[1]),
        "z_ned_m": -float(altitude),
        "altitude_m": float(altitude),
        "marker_detected": int(bool(detected)),
        "marker_error_x": error_x,
        "marker_error_y": error_y,
        "marker_error_norm": error_norm,
        "landing_confidence": float(confidence),
        "marker_sigma_x_m": sigma_x,
        "marker_sigma_y_m": sigma_y,
        "marker_sigma_radial_m": sigma_radial,
        "safe_to_descend": int(bool(safe)),
    }
