from __future__ import annotations

from functools import lru_cache

from plc_platform_backend.runs.runs_models import Run
from plc_platform_backend.runs.runs_repository import (
    RunsRepository,
    get_runs_repository,
)


@lru_cache
def get_runs_service() -> RunsService:
    _run_service = RunsService()
    return _run_service


class RunsService:

    def __init__(self) -> None:
        self.runs_repository: RunsRepository = get_runs_repository()

    async def save_run(self, run: Run) -> Run:
        return Run.from_document(await self.runs_repository.create_run(run))

    async def find_by_id(self, run_id: str) -> Run:
        return Run.from_document(await self.runs_repository.get_run(run_id))

    async def get_all(self) -> list[Run]:
        return [Run.from_document(run) for run in await self.runs_repository.get_all()]
