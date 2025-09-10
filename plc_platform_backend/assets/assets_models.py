from enum import Enum, IntEnum


class TestbenchNodeDepth(IntEnum):
    ORIGINAL_TRACKS = 0
    SAMPLE_MASKS = 1
    RECONSTRUCTED_TRACKS = 2
    OUTPUT_ANALYSIS = 3
