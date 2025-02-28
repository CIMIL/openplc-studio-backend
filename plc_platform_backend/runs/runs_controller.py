from typing import Annotated

from fastapi import APIRouter, Depends

from plc_platform_backend.runs.runs_models import Run
from plc_platform_backend.runs.runs_service import RunsService, get_runs_service

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.post("", status_code=201)
async def create_run(
    run: Run,
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> Run:
    return runs_service.save_run(run)


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> Run:
    return runs_service.find_by_id(run_id)


@router.get("")
async def get_all_runs(
    runs_service: Annotated[RunsService, Depends(get_runs_service)],
) -> list[Run]:
    return runs_service.get_all()
