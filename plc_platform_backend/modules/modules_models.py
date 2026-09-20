from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel

from plc_platform_backend.commons.base_document import BaseDocument

from pydantic import BaseModel, Field


class ModuleType(str, Enum):
    PacketLossSimulator = "PacketLossSimulator"
    PLCAlgorithm = "PLCAlgorithm"
    OutputAnalyser = "OutputAnalyser"
    CrossfadeSettings = "CrossfadeSettings"


class ParameterValidation(BaseModel):
    min: float | None = None
    max: float | None = None
    step: float | None = None
    exclusive_min: bool = False
    exclusive_max: bool = False
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    unique: bool = False
    sorted: Literal["ascending", "descending"] | None = None
    item: ParameterValidation | None = None


class ModuleConstraint(BaseModel):
    type: Literal[
        "less_than",
        "length_relation",
        "keys_match",
        "per_key_length_relation",
    ]
    setting: str
    related_setting: str | None = None
    offset: int | None = None
    allowed_key_sets: list[list[str]] | None = None
    message: str | None = None


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
    values: Optional[list[Any]] = None
    validation: Optional[ParameterValidation] = None


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
    node_ids: list[str] = Field(default_factory=lambda: [])
    settings: list[ModuleParameterDocument]


class ModuleSpec(BaseModel):
    name: str
    settings: list[ModuleParameterSpec]
    constraints: list[ModuleConstraint] = Field(default_factory=lambda: [])


class Module(BaseModel):
    name: str
    node_ids: list[str] = Field(default_factory=lambda: [])
    settings: list[ModuleParameter]

    @staticmethod
    def from_document(document: ModuleDocument) -> Module:
        return Module(
            name=document.name,
            settings=[
                (ModuleParameter.from_document(param)) for param in document.settings
            ],
        )
