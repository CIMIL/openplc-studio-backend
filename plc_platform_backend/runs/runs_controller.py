import io
import os
import tempfile
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from plc_platform_backend.assets.assets_models import TestbenchNodeDepth
from plc_platform_backend.runs.runs_models import Run
from plc_platform_backend.runs.runs_service import RunsService, get_runs_service

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "",
    status_code=201,
)
async def create_run(
    run: Run,
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> Run:
    return await runs_service.save_run(run)


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> Run:
    return await runs_service.find_by_id(run_id)


@router.get("/{run_id}/assets/{depth}")
async def get_run_assets_paths(
    run_id: str,
    depth: int,
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> FileResponse:
    tar_archive: io.BytesIO = await runs_service.get_assets_tar_by_depth(
        run_id, TestbenchNodeDepth(depth)
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp:
        tmp.write(tar_archive.getvalue())
        tmp.flush()
        tmp = tmp.name

    return FileResponse(
        tmp,
        media_type="application/octet-stream",
        filename=f"run_{run_id}_assets_depth_{depth}.tar",
        background=BackgroundTasks([lambda: os.unlink(tmp)]),
    )


@router.get("")
async def get_all_runs(
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> list[Run]:
    return await runs_service.get_all()
