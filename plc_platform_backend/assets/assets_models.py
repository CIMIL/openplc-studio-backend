from enum import Enum, IntEnum

from pydantic import BaseModel


class TestbenchNodeDepth(IntEnum):
    ORIGINAL_TRACKS = 0
    SAMPLE_MASKS = 1
    RECONSTRUCTED_TRACKS = 2
    OUTPUT_ANALYSIS = 3


class OriginalTrackMetadata(BaseModel):
    name: str
    size_bytes: int
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_depth: int | None = None
