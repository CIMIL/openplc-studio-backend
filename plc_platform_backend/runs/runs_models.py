from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from plc_platform_backend.commons.base_document import BaseDocument
from plc_platform_backend.modules.modules_models import Module


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class RunDocument(BaseDocument):
    author: str
    name: str
    packet_size: int
    status: RunStatus = RunStatus.CREATED
    modules: list[Module]


class Run(BaseModel):
    author: str
    name: str
    packet_size: int
    status: RunStatus = RunStatus.CREATED
    modules: list[Module]

    @staticmethod
    def from_document(document: RunDocument) -> Run:
        return Run(
            author=document.author,
            name=document.name,
            status=document.status,
            config=document.config,
        )
