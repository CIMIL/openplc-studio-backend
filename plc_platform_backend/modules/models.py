from enum import Enum


class ModuleType(str, Enum):
    PacketLossSimulator = "PacketLossSimulator"
    PLCAlgorithm = "PLCAlgorithm"
    OutputAnalyser = "OutputAnalyser"
