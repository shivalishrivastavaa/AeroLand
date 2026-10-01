"""Validated public models for the AeroLand mission service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    """Mission settings accepted at the API boundary."""

    mission_name: str = Field(default="Inspection + precision landing", max_length=80)
    confidence_threshold: float = Field(default=0.60, ge=0.40, le=0.95)
    sigma_threshold_m: float = Field(default=0.12, ge=0.05, le=0.30)
    cruise_altitude_m: float = Field(default=2.50, ge=1.50, le=4.00)
    wind_speed_mps: float = Field(default=0.0, ge=0.0, le=8.0)
    random_seed: int = Field(default=7, ge=0, le=2147483647)


class MissionStatus(BaseModel):
    """Current state of one asynchronous mission."""

    run_id: str
    status: Literal["queued", "running", "complete", "failed", "cancelled"]
    progress: float = Field(ge=0.0, le=1.0)
    current_state: str
    runner: Literal["demo", "gazebo"]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, float | int | str] | None = None
    error: str | None = None


class HealthStatus(BaseModel):
    """Backend readiness and runner capabilities."""

    status: Literal["ok", "not_ready"]
    runner: Literal["demo", "gazebo"]
    detail: str
    supports_wind: bool
    supports_seed: bool
