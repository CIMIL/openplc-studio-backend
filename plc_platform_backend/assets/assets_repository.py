from __future__ import annotations

import os
import pathlib
from functools import lru_cache

import soundfile as sf
from plctestbench.models import TestbenchConfiguration
from plctestbench.node import Node
from plctestbench.plc_testbench import PLCTestbench

from plc_platform_backend.assets.assets_models import (
    OriginalTrackMetadata,
    TestbenchNodeDepth,
)
from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.runs.runs_models import Run

# Maps libsndfile subtype names to a bit depth for the supported WAV encodings.
_SUBTYPE_BIT_DEPTH: dict[str, int] = {
    "PCM_S8": 8,
    "PCM_U8": 8,
    "PCM_16": 16,
    "PCM_24": 24,
    "PCM_32": 32,
    "FLOAT": 32,
    "DOUBLE": 64,
}


@lru_cache
def get_assets_repository() -> AssetsRepository:
    _file_repository = AssetsRepository()
    return _file_repository


class AssetsRepository:

    def __init__(self) -> None:
        pass

    async def save_file(self, content: bytes, filename: str) -> None:
        path = pathlib.Path(self.get_original_track_basepath(), filename)

        try:
            with open(path, "wb") as f:
                f.write(content)
        except OSError as error:
            raise OSError(f"Could not save asset '{filename}': {error}") from error

    async def get_all_original_track_filenames(self) -> list[str]:
        tracks_basepath = self.get_original_track_basepath()
        try:
            entries = os.listdir(tracks_basepath)
        except OSError as error:
            raise OSError(
                f"Could not list tracks in '{tracks_basepath}': {error}"
            ) from error

        return [
            f
            for f in entries
            if os.path.isfile(os.path.join(tracks_basepath, f))
            and f.lower().endswith(".wav")
        ]

    async def get_all_original_track_metadata(self) -> list[OriginalTrackMetadata]:
        tracks_basepath = self.get_original_track_basepath()
        try:
            entries = sorted(os.listdir(tracks_basepath))
        except OSError as error:
            raise OSError(
                f"Could not list tracks in '{tracks_basepath}': {error}"
            ) from error

        metadata: list[OriginalTrackMetadata] = []
        for filename in entries:
            path = os.path.join(tracks_basepath, filename)
            if not os.path.isfile(path) or not filename.lower().endswith(".wav"):
                continue
            metadata.append(self._read_track_metadata(path, filename))
        return metadata

    @staticmethod
    def _read_track_metadata(path: str, filename: str) -> OriginalTrackMetadata:
        size_bytes = os.path.getsize(path)
        try:
            info = sf.info(path)
        except (RuntimeError, ValueError, OSError):
            # Unreadable/unsupported file: keep what we can still report.
            return OriginalTrackMetadata(name=filename, size_bytes=size_bytes)

        try:
            return OriginalTrackMetadata(
                name=filename,
                size_bytes=size_bytes,
                duration_seconds=float(info.duration),
                sample_rate=int(info.samplerate),
                channels=int(info.channels),
                bit_depth=_SUBTYPE_BIT_DEPTH.get(info.subtype),
            )
        except (TypeError, ValueError):
            return OriginalTrackMetadata(name=filename, size_bytes=size_bytes)

    def get_root_folder(self) -> pathlib.Path:
        root_folder = get_configuration().plc_root_folder
        root_folder = pathlib.Path(root_folder).resolve()
        return root_folder

    def get_original_track_basepath(self) -> pathlib.Path:
        return self.get_root_folder()

    def get_assets_paths(
        self,
        run: Run,
        depth: TestbenchNodeDepth,
        testbench_settings: TestbenchConfiguration,
    ) -> list[str]:

        testbench = PLCTestbench(
            run_id=run.testbench_internal_id,
            testbench_settings=testbench_settings,
        )

        nodes: list[Node] = testbench.data_manager.get_nodes_by_depth(depth)

        return [f.get_path() for f in nodes]

    def resolve_asset_path(self, stem: str, depth: TestbenchNodeDepth) -> str:
        if depth == TestbenchNodeDepth.SAMPLE_MASKS:
            return f"{stem}.npy"
        elif (
            depth == TestbenchNodeDepth.ORIGINAL_TRACKS
            or depth == TestbenchNodeDepth.RECONSTRUCTED_TRACKS
        ):
            return f"{stem}.wav"
        elif depth == TestbenchNodeDepth.OUTPUT_ANALYSIS:
            return f"{stem}.pickle"
