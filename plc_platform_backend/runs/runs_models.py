from __future__ import annotations

from enum import Enum

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
    status: RunStatus = RunStatus.CREATED
    modules: dict[ModuleType, list[Module]]


class Run(BaseModel):
    author: str
    name: str
    status: RunStatus = RunStatus.CREATED
    modules: dict[ModuleType, list[Module]]

    @staticmethod
    def from_document(document: RunDocument) -> Run:
        return Run(
            author=document.author,
            name=document.name,
            status=document.status,
            modules=document.modules,
        )
