from __future__ import annotations

import os
import pathlib
from functools import lru_cache

from plctestbench.models import TestbenchConfiguration
from plctestbench.node import Node
from plctestbench.plc_testbench import PLCTestbench

from plc_platform_backend.assets.assets_models import TestbenchNodeDepth
from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.runs.runs_models import Run


@lru_cache
def get_assets_repository() -> AssetsRepository:
    _file_repository = AssetsRepository()
    return _file_repository


class AssetsRepository:

    def __init__(self) -> None:
        pass

    async def save_file(self, content: bytes, filename: str) -> None:
        path = pathlib.Path(self.get_original_track_basepath(), filename)

        with open(path, "wb") as f:
            f.write(content)

    async def get_all_original_track_filenames(self) -> list[str]:
        tracks_basepath = self.get_original_track_basepath()
        return [
            f
            for f in os.listdir(tracks_basepath)
            if os.path.isfile(os.path.join(tracks_basepath, f)) and f.endswith(".wav")
        ]

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
