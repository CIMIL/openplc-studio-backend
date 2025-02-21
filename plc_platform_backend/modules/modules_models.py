from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from plc_platform_backend.commons.base_document import BaseDocument


class ModuleType(str, Enum):
    PacketLossSimulator = "PacketLossSimulator"
    PLCAlgorithm = "PLCAlgorithm"
    OutputAnalyser = "OutputAnalyser"
    CrossfadeSettings = "CrossfadeSettings"


class ModuleParameterDocument(BaseDocument):
    name: str
    type: str
    default: Any
    value: Any
    values: Optional[list[Any]]


class ModuleParameter(BaseModel):
    name: str
    type: str
    default: Any
    value: Any
    values: Optional[list[Any]]

    @staticmethod
    def from_document(document: ModuleParameterDocument) -> ModuleParameter:
        return ModuleParameter(
            name=document.name,
            type=document.type,
            default=document.default,
            value=document.value,
            values=document.values,
        )


class ModuleDocument(BaseDocument):
    name: str
    settings: list[ModuleParameterDocument]


class Module(BaseModel):
    name: str
    settings: list[ModuleParameter]

    @staticmethod
    def from_document(document: ModuleDocument) -> Module:
        return Module(
            name=document.name,
            settings=[
                ModuleParameter.from_document(param) for param in document.settings
            ],
        )
