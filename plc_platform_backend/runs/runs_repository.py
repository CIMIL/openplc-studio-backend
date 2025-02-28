from __future__ import annotations

from functools import lru_cache

from bson import ObjectId

from plc_platform_backend.commons.base_mongodb_repository import BaseMongoDBRepository
from plc_platform_backend.db.db_client import MongoDB, get_mongodb
from plc_platform_backend.runs.runs_models import Run, RunDocument

COLLECTION_NAME = "runs"


@lru_cache
def get_runs_repository() -> RunsRepository:
    _module_service = RunsRepository()
    return _module_service


class RunsRepository(BaseMongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_NAME)

    def create_run(self, run: Run) -> RunDocument:
        run_document = RunDocument(
            author=run.author, name=run.name, status=run.status, modules=run.modules
        )
        run_dict = run_document.model_dump()
        self.collection.insert_one(run_dict)
        return run_document

    def get_run(self, run_id: str) -> RunDocument:
        run_data = self.collection.find_one({"_id": ObjectId(run_id)})
        return RunDocument(**run_data) if run_data else None

    def get_all(self) -> list[RunDocument]:
        runs_data = self.collection.find()
        return [RunDocument(**run_data) for run_data in runs_data]

    def update_run(self, run_id: str, updated_run: Run) -> bool:
        result = self.collection.update_one(
            {"_id": ObjectId(run_id)}, {"$set": updated_run.dict()}
        )
        return result.modified_count > 0

    def delete_run(self, run_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(run_id)})
        return result.deleted_count > 0
