from enum import Enum
from typing import Any

from pydantic import BaseModel


class ModuleType(str, Enum):
    PacketLossSimulator = "PacketLossSimulator"
    PLCAlgorithm = "PLCAlgorithm"
    OutputAnalyser = "OutputAnalyser"


class ModuleParameters(BaseModel):
    name: str
    type: str
    default: Any


class Module(BaseModel):
    name: str
    settings: list[ModuleParameters]
