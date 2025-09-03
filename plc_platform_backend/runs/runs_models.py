from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from plc_platform_backend.commons.base_document import BaseDocument
from plc_platform_backend.modules.modules_models import Module, ModuleType


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class RunDocument(BaseDocument):
    author: str
    name: str
    testbench_internal_id: str
    status: RunStatus = RunStatus.CREATED
    tracks: list[str]
    modules: dict[ModuleType, list[Module]]


class Run(BaseModel):
    author: str
    name: str
    testbench_internal_id: Optional[str]
    status: RunStatus = RunStatus.CREATED
    tracks: list[str]
    modules: dict[ModuleType, list[Module]]

    @staticmethod
    def from_document(document: RunDocument) -> Run:
        return Run(
            author=document.author,
            name=document.name,
            testbench_internal_id=document.testbench_internal_id,
            status=document.status,
            tracks=document.tracks,
            modules=document.modules,
        )
