from enum import Enum
from typing import Any, Optional

from matplotlib.style import available
from pydantic import BaseModel


class ModuleType(str, Enum):
    PacketLossSimulator = "PacketLossSimulator"
    PLCAlgorithm = "PLCAlgorithm"
    OutputAnalyser = "OutputAnalyser"


class ModuleParameters(BaseModel):
    name: str
    type: str
    default: Any
    values: Optional[list[Any]]


class Module(BaseModel):
    name: str
    settings: list[ModuleParameters]
