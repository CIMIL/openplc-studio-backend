from __future__ import annotations

from functools import lru_cache

from bson import ObjectId

from plc_platform_backend.commons.base_mongodb_repository import BaseMongoDBRepository
from plc_platform_backend.runs.runs_models import Run, RunCreateDto, RunDocument

COLLECTION_NAME = "runs"


@lru_cache
def get_runs_repository() -> RunsRepository:
    _module_service = RunsRepository()
    return _module_service


class RunsRepository(BaseMongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_NAME)

    async def create_run(self, run: RunCreateDto) -> RunDocument:
        run_document = RunDocument(
            author=run.author,
            name=run.name,
            testbench_internal_id=run.testbench_internal_id,
            status=run.status,
            tracks=run.tracks,
            modules=run.modules,
        )

        run_document = await self.collection.insert_one(
            run_document.model_dump(by_alias=True, exclude=["id"])
        )

        run_document = await self.get_run(run_document.inserted_id)

        return run_document

    async def get_run(self, run_id: str) -> RunDocument:
        run_data = await self.collection.find_one({"_id": ObjectId(run_id)})
        return RunDocument(**run_data) if run_data else None

    async def get_all(self) -> list[RunDocument]:
        runs_data = await self.collection.find().to_list(1000)
        return [RunDocument(**run_data) for run_data in runs_data]

    async def update_run(self, run_id: str, updated_run: Run) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(run_id)}, {"$set": updated_run.model_dump()}
        )
        return result.modified_count > 0

    def delete_run(self, run_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(run_id)})
        return result.deleted_count > 0
