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


class ModuleParameterSpec(BaseModel):
    name: str
    type: str
    default: Any
    values: Optional[list[Any]]


class ModuleParameter(BaseModel):
    name: str
    value: Any

    @staticmethod
    def from_document(document: ModuleParameterDocument) -> ModuleParameterSpec:
        return ModuleParameterSpec(
            name=document.name,
            value=document.value,
        )


class ModuleDocument(BaseDocument):
    name: str
    testbench_node_id: str
    settings: list[ModuleParameterDocument]


class ModuleSpec(BaseModel):
    name: str
    settings: list[ModuleParameterSpec]


class Module(BaseModel):
    name: str
    testbench_node_id: Optional[str] = None
    settings: list[ModuleParameter]

    @staticmethod
    def from_document(document: ModuleDocument) -> Module:
        return Module(
            name=document.name,
            testbench_node_id=document.testbench_node_id,
            settings=[
                (ModuleParameter.from_document(param)) for param in document.settings
            ],
        )
