"""FastAPI boundary for local AeroLand mission execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from threading import Event, Lock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from aeroland_web.simulation import MissionConfig, MissionResult
from backend.models import HealthStatus, MissionRequest, MissionStatus
from backend.runners import MissionCancelled, runner_from_environment


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunRecord:
    """Private mutable state for one mission."""

    run_id: str
    request: MissionRequest
    runner: str
    created_at: str = field(default_factory=_timestamp)
    status: str = "queued"
    progress: float = 0.0
    current_state: str = "QUEUED"
    started_at: str | None = None
    finished_at: str | None = None
    result: MissionResult | None = None
    error: str | None = None
    cancel_event: Event = field(default_factory=Event)


runner = runner_from_environment()
executor = ThreadPoolExecutor(max_workers=1 if runner.name == "gazebo" else 4)
runs: dict[str, RunRecord] = {}
runs_lock = Lock()

app = FastAPI(
    title="AeroLand Mission API",
    version="0.2.0",
    description="Validated boundary for demo or isolated PX4/Gazebo mission runs.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "AEROLAND_ALLOWED_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


def _get_record(run_id: str) -> RunRecord:
    with runs_lock:
        record = runs.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown mission run")
        return record


def _status(record: RunRecord) -> MissionStatus:
    return MissionStatus(
        run_id=record.run_id,
        status=record.status,
        progress=record.progress,
        current_state=record.current_state,
        runner=record.runner,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        result=record.result.metrics if record.result else None,
        error=record.error,
    )


def _run_mission(record: RunRecord) -> None:
    with runs_lock:
        record.status = "running"
        record.current_state = "INITIALIZING"
        record.started_at = _timestamp()

    def update(progress: float, state: str) -> None:
        with runs_lock:
            record.progress = max(record.progress, min(float(progress), 0.99))
            record.current_state = state

    config = MissionConfig(**record.request.model_dump())
    try:
        result = runner.run(
            record.run_id,
            config,
            record.cancel_event,
            update,
        )
        with runs_lock:
            record.result = result
            record.status = "complete"
            record.progress = 1.0
            record.current_state = "COMPLETE"
            record.finished_at = _timestamp()
    except MissionCancelled as error:
        with runs_lock:
            record.status = "cancelled"
            record.current_state = "CANCELLED"
            record.error = str(error)
            record.finished_at = _timestamp()
    except Exception as error:  # pragma: no cover - defensive process boundary
        with runs_lock:
            record.status = "failed"
            record.current_state = "FAILED"
            record.error = str(error)
            record.finished_at = _timestamp()


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    ready, detail = runner.health()
    return HealthStatus(
        status="ok" if ready else "not_ready",
        runner=runner.name,
        detail=detail,
        supports_wind=runner.supports_wind,
        supports_seed=runner.supports_seed,
    )


@app.get("/v1/gazebo-view/status")
def gazebo_view_status(response: Response) -> dict[str, bool | str]:
    """Tell the browser when it is safe to open one Gazebo WebSocket."""

    response.headers["Cache-Control"] = "no-store"
    status_provider = getattr(runner, "gazebo_view_status", None)
    if status_provider is None:
        return {
            "ready": False,
            "state": "unavailable",
            "detail": "This mission runner does not provide a live Gazebo view.",
        }
    return status_provider()


@app.post("/v1/gazebo-view/client-ready")
def gazebo_view_client_ready(response: Response) -> dict[str, bool | str]:
    """Let the runner know that the browser has rendered the drone model."""

    response.headers["Cache-Control"] = "no-store"
    ready_provider = getattr(runner, "gazebo_view_client_ready", None)
    if ready_provider is None:
        return {
            "accepted": False,
            "client_ready": False,
        }
    return ready_provider()


@app.post("/v1/missions", response_model=MissionStatus, status_code=202)
def create_mission(request: MissionRequest) -> MissionStatus:
    run_id = uuid4().hex
    record = RunRecord(run_id=run_id, request=request, runner=runner.name)
    with runs_lock:
        runs[run_id] = record
    executor.submit(_run_mission, record)
    return _status(record)


@app.get("/v1/missions/{run_id}", response_model=MissionStatus)
def mission_status(run_id: str) -> MissionStatus:
    return _status(_get_record(run_id))


@app.get("/v1/missions/{run_id}/telemetry")
def mission_telemetry(run_id: str) -> Response:
    record = _get_record(run_id)
    if record.status != "complete" or record.result is None:
        raise HTTPException(status_code=409, detail="Mission telemetry is not ready")
    return Response(
        content=record.result.telemetry.to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run_id}_telemetry.csv"'},
    )


@app.delete("/v1/missions/{run_id}", response_model=MissionStatus)
def cancel_mission(run_id: str) -> MissionStatus:
    record = _get_record(run_id)
    if record.status in {"queued", "running"}:
        record.cancel_event.set()
        with runs_lock:
            record.current_state = "CANCELLING"
    return _status(record)


@app.websocket("/v1/missions/{run_id}/events")
async def mission_events(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            record = _get_record(run_id)
            payload: dict[str, Any] = _status(record).model_dump()
            await websocket.send_json(payload)
            if record.status in {"complete", "failed", "cancelled"}:
                break
            import asyncio

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return


def _px4_gazebo_model_asset(
    model_name: str,
    asset_directory: str,
    asset_path: str,
) -> FileResponse:
    """Serve one PX4 model asset without exposing arbitrary local files."""

    px4_directory = Path(
        os.getenv("PX4_AUTOPILOT_DIR", str(Path.home() / "PX4-Autopilot"))
    )
    models_directory = (
        px4_directory / "Tools" / "simulation" / "gz" / "models"
    ).resolve()
    requested_file = (
        models_directory / model_name / asset_directory / asset_path
    ).resolve()

    try:
        requested_file.relative_to(models_directory)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Unknown Gazebo asset") from error

    if not requested_file.is_file():
        raise HTTPException(status_code=404, detail="Unknown Gazebo asset")

    return FileResponse(
        path=requested_file,
        headers={"Cache-Control": "no-store"},
    )


@app.api_route(
    "/gazebo-view/{model_name}/meshes/{asset_path:path}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
def gazebo_mesh_asset(model_name: str, asset_path: str) -> FileResponse:
    """Provide Collada and other PX4 mesh files to the embedded viewer."""

    return _px4_gazebo_model_asset(model_name, "meshes", asset_path)


@app.api_route(
    "/gazebo-view/{model_name}/materials/{asset_path:path}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
def gazebo_material_asset(model_name: str, asset_path: str) -> FileResponse:
    """Provide PX4 model textures and material files to the embedded viewer."""

    return _px4_gazebo_model_asset(model_name, "materials", asset_path)


gazebo_view_directory = Path(__file__).resolve().parents[1] / "gazebo_view"
if gazebo_view_directory.is_dir():
    app.mount(
        "/gazebo-view",
        StaticFiles(directory=str(gazebo_view_directory), html=True),
        name="gazebo-view",
    )
