"""Plotly visualizations for the AeroLand operations console."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .simulation import STATE_ORDER


CYAN = "#F0B95A"
BLUE = "#F3F0E8"
PURPLE = "#C8A7FF"
AMBER = "#6FDC9B"
RED = "#FF6078"
GRID = "rgba(145, 139, 126, 0.13)"
MUTED = "#918D84"
TEXT = "#F3F0E8"
PANEL = "#05090E"


def _base_layout(figure: go.Figure, height: int = 340) -> go.Figure:
    """Apply the shared technical chart theme."""

    figure.update_layout(
        height=height,
        margin=dict(l=44, r=22, t=42, b=42),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(1,5,8,0.72)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT, size=11),
        hoverlabel=dict(
            bgcolor="#050A0F",
            bordercolor="#243C4B",
            font=dict(family="ui-monospace, SFMono-Regular, Menlo, monospace"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=1,
            font=dict(size=10, color=MUTED),
        ),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=MUTED, activecolor=CYAN),
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont=dict(family="ui-monospace, SFMono-Regular, Menlo, monospace"),
        title_font=dict(color=MUTED, size=10),
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont=dict(family="ui-monospace, SFMono-Regular, Menlo, monospace"),
        title_font=dict(color=MUTED, size=10),
    )
    return figure


def mission_view(frame: pd.DataFrame, index: int) -> go.Figure:
    """Render the completed and remaining 3-D trajectory."""

    index = min(max(int(index), 0), len(frame) - 1)
    flown = frame.iloc[: index + 1]
    remaining = frame.iloc[index:]
    current = frame.iloc[index]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter3d(
            x=remaining["x_m"],
            y=remaining["y_m"],
            z=remaining["altitude_m"],
            mode="lines",
            line=dict(color="rgba(87,116,137,0.25)", width=3, dash="dot"),
            name="planned trace",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=flown["x_m"],
            y=flown["y_m"],
            z=flown["altitude_m"],
            mode="lines",
            line=dict(color=CYAN, width=6),
            name="flight path",
            hovertemplate="X %{x:.2f} m<br>Y %{y:.2f} m<br>ALT %{z:.2f} m<extra></extra>",
        )
    )
    theta = np.linspace(0.0, 2.0 * math.pi, 80)
    figure.add_trace(
        go.Scatter3d(
            x=0.15 * np.cos(theta),
            y=0.15 * np.sin(theta),
            z=np.zeros_like(theta),
            mode="lines",
            line=dict(color=AMBER, width=5),
            name="landing target",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[current["x_m"]],
            y=[current["y_m"]],
            z=[current["altitude_m"]],
            mode="markers",
            marker=dict(
                size=8,
                color=CYAN if current["mission_state"] != "ABORTED" else RED,
                symbol="diamond",
                line=dict(color="#DFFFFB", width=2),
            ),
            name="vehicle",
            hovertemplate=(
                f"STATE {current['mission_state']}<br>"
                f"T+ {current['elapsed_seconds']:.1f} s<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=475,
        margin=dict(l=0, r=0, t=14, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=10),
        showlegend=False,
        scene=dict(
            bgcolor="rgba(0,3,6,0.72)",
            aspectmode="manual",
            aspectratio=dict(x=1.1, y=1.0, z=0.82),
            camera=dict(eye=dict(x=1.48, y=1.48, z=1.15)),
            xaxis=dict(
                title="X / m",
                range=[-0.35, 1.75],
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor=GRID,
                zerolinecolor=GRID,
                color=MUTED,
            ),
            yaxis=dict(
                title="Y / m",
                range=[-0.35, 1.75],
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor=GRID,
                zerolinecolor=GRID,
                color=MUTED,
            ),
            zaxis=dict(
                title="ALT / m",
                range=[0.0, max(float(frame["altitude_m"].max()) * 1.15, 1.0)],
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor=GRID,
                zerolinecolor=GRID,
                color=MUTED,
            ),
        ),
    )
    return figure


def sensor_reticle(row: pd.Series) -> go.Figure:
    """Render a technical downward-camera landing-target view."""

    detected = bool(row["marker_detected"])
    x_value = float(row["marker_error_x"]) if detected else 0.0
    y_value = float(row["marker_error_y"]) if detected else 0.0
    figure = go.Figure()

    # Range rings and crosshair.
    for radius, opacity in [(0.30, 0.18), (0.20, 0.25), (0.10, 0.38)]:
        figure.add_shape(
            type="circle",
            x0=-radius,
            y0=-radius,
            x1=radius,
            y1=radius,
            line=dict(color=f"rgba(49,230,210,{opacity})", width=1),
        )
    figure.add_shape(type="line", x0=-0.34, x1=0.34, y0=0, y1=0, line=dict(color=GRID))
    figure.add_shape(type="line", x0=0, x1=0, y0=-0.34, y1=0.34, line=dict(color=GRID))
    figure.add_shape(
        type="rect",
        x0=-0.045,
        x1=0.045,
        y0=-0.045,
        y1=0.045,
        line=dict(color=AMBER, width=2),
    )

    if detected:
        figure.add_trace(
            go.Scatter(
                x=[x_value],
                y=[y_value],
                mode="markers",
                marker=dict(
                    symbol="x",
                    size=18,
                    color=CYAN,
                    line=dict(width=2, color=CYAN),
                ),
                name="marker centroid",
                hovertemplate="ERR X %{x:.3f}<br>ERR Y %{y:.3f}<extra></extra>",
            )
        )
        figure.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=x_value,
            y1=y_value,
            line=dict(color="rgba(49,230,210,0.45)", dash="dot"),
        )

    status_color = CYAN if detected else RED
    status_text = "MARKER LOCK" if detected else "NO VISUAL LOCK"
    figure.add_annotation(
        x=-0.325,
        y=0.31,
        text=status_text,
        showarrow=False,
        xanchor="left",
        font=dict(
            family="ui-monospace, SFMono-Regular, Menlo, monospace",
            size=11,
            color=status_color,
        ),
    )
    figure.update_layout(
        height=390,
        margin=dict(l=18, r=18, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,3,6,0.76)",
        showlegend=False,
        xaxis=dict(range=[-0.35, 0.35], visible=False, constrain="domain"),
        yaxis=dict(range=[-0.35, 0.35], visible=False, scaleanchor="x", scaleratio=1),
    )
    return figure


def altitude_chart(frame: pd.DataFrame) -> go.Figure:
    """Altitude profile with mission-state hover context."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["elapsed_seconds"],
            y=frame["altitude_m"],
            mode="lines",
            line=dict(color=PURPLE, width=2),
            fill="tozeroy",
            fillcolor="rgba(155,123,255,0.17)",
            customdata=frame[["mission_state"]],
            hovertemplate="T+ %{x:.1f} s<br>ALT %{y:.2f} m<br>%{customdata[0]}<extra></extra>",
            name="altitude",
        )
    )
    figure.update_layout(title=dict(text="ALTITUDE PROFILE", font=dict(size=11, color=MUTED)))
    figure.update_xaxes(title="ELAPSED TIME / s")
    figure.update_yaxes(title="ALTITUDE / m", rangemode="tozero")
    return _base_layout(figure, 330)


def confidence_chart(frame: pd.DataFrame, threshold: float) -> go.Figure:
    """Confidence trace and closed-loop descent approval."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["elapsed_seconds"],
            y=frame["landing_confidence"],
            mode="lines",
            line=dict(color=BLUE, width=2),
            name="confidence",
            hovertemplate="T+ %{x:.1f} s<br>CONF %{y:.3f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["elapsed_seconds"],
            y=frame["safe_to_descend"],
            mode="lines",
            line=dict(color=CYAN, width=2, shape="hv"),
            name="descent gate",
            hovertemplate="T+ %{x:.1f} s<br>GATE %{y}<extra></extra>",
        )
    )
    figure.add_hline(
        y=threshold,
        line=dict(color=RED, width=1.5, dash="dash"),
        annotation_text=f"LIMIT {threshold:.2f}",
        annotation_font=dict(size=9, color=RED),
        annotation_position="top left",
    )
    figure.update_layout(title=dict(text="LANDING CONFIDENCE + DESCENT GATE", font=dict(size=11, color=MUTED)))
    figure.update_xaxes(title="ELAPSED TIME / s")
    figure.update_yaxes(title="SCORE / BOOLEAN", range=[-0.04, 1.06])
    return _base_layout(figure, 330)


def sigma_chart(frame: pd.DataFrame, threshold: float) -> go.Figure:
    """Ground-plane uncertainty components and radial limit."""

    figure = go.Figure()
    for column, name, color in [
        ("marker_sigma_radial_m", "radial σ", PURPLE),
        ("marker_sigma_x_m", "σx", BLUE),
        ("marker_sigma_y_m", "σy", AMBER),
    ]:
        figure.add_trace(
            go.Scatter(
                x=frame["elapsed_seconds"],
                y=frame[column],
                mode="lines",
                line=dict(color=color, width=2 if "radial" in name else 1.3),
                name=name,
                connectgaps=False,
                hovertemplate=f"T+ %{{x:.1f}} s<br>{name.upper()} %{{y:.3f}} m<extra></extra>",
            )
        )
    figure.add_hline(
        y=threshold,
        line=dict(color=RED, width=1.5, dash="dash"),
        annotation_text=f"LIMIT {threshold:.3f} m",
        annotation_font=dict(size=9, color=RED),
        annotation_position="top left",
    )
    figure.update_layout(title=dict(text="GROUND-PLANE UNCERTAINTY", font=dict(size=11, color=MUTED)))
    figure.update_xaxes(title="ELAPSED TIME / s")
    figure.update_yaxes(title="STANDARD DEVIATION / m", rangemode="tozero")
    return _base_layout(figure, 330)


def state_chart(frame: pd.DataFrame) -> go.Figure:
    """Stepped mission-state timeline."""

    state_index = {state: index for index, state in enumerate(STATE_ORDER)}
    values = [state_index.get(str(state), -1) for state in frame["mission_state"]]
    figure = go.Figure(
        go.Scatter(
            x=frame["elapsed_seconds"],
            y=values,
            mode="lines",
            line=dict(color=CYAN, width=2.4, shape="hv"),
            customdata=frame[["mission_state"]],
            hovertemplate="T+ %{x:.1f} s<br>%{customdata[0]}<extra></extra>",
            name="mission state",
        )
    )
    used_states = [state for state in STATE_ORDER if state in set(frame["mission_state"])]
    figure.update_layout(title=dict(text="MISSION-STATE SEQUENCE", font=dict(size=11, color=MUTED)))
    figure.update_xaxes(title="ELAPSED TIME / s")
    figure.update_yaxes(
        title="STATE",
        tickmode="array",
        tickvals=[state_index[state] for state in used_states],
        ticktext=used_states,
    )
    return _base_layout(figure, 330)


def error_chart(frame: pd.DataFrame) -> go.Figure:
    """Marker-centering error in the camera-normalized plane."""

    detected = frame[frame["marker_detected"] == 1]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=detected["marker_error_x"],
            y=detected["marker_error_y"],
            mode="lines+markers",
            line=dict(color="rgba(49,230,210,0.45)", width=1),
            marker=dict(
                size=4,
                color=detected["elapsed_seconds"],
                colorscale=[[0, BLUE], [0.55, PURPLE], [1, CYAN]],
                showscale=True,
                colorbar=dict(title="T+ / s", thickness=9, len=0.7),
            ),
            hovertemplate="ERR X %{x:.3f}<br>ERR Y %{y:.3f}<extra></extra>",
            name="marker error",
        )
    )
    figure.add_shape(
        type="circle",
        x0=-0.10,
        x1=0.10,
        y0=-0.10,
        y1=0.10,
        line=dict(color=AMBER, dash="dash"),
    )
    figure.add_trace(
        go.Scatter(
            x=[0],
            y=[0],
            mode="markers",
            marker=dict(symbol="cross", size=10, color=AMBER),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.update_layout(
        title=dict(text="MARKER-CENTERING CONVERGENCE", font=dict(size=11, color=MUTED)),
    )
    figure.update_xaxes(title="NORMALIZED ERROR X", range=[-0.34, 0.34])
    figure.update_yaxes(
        title="NORMALIZED ERROR Y",
        range=[-0.34, 0.34],
        scaleanchor="x",
        scaleratio=1,
    )
    return _base_layout(figure, 390)
