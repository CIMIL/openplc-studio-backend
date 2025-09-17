from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from tarfile import TarFile, TarInfo

import numpy as np

from plc_platform_backend.assets.assets_repository import (
    AssetsRepository,
    get_assets_repository,
)


@lru_cache
def get_assets_service() -> AssetsService:
    _file_service = AssetsService()
    return _file_service


class AssetsService:

    def __init__(self) -> None:
        self.assets_repository: AssetsRepository = get_assets_repository()

    async def save_file(self, data: bytes, filename: str) -> None:
        await self.assets_repository.save_file(data, filename)

    async def get_all_original_track_filenames(self) -> list[str]:
        return await self.assets_repository.get_all_original_track_filenames()

    def add_json_to_tar(
        self, data: np.ndarray, tar: TarFile, original_path: str, original_ext: str
    ) -> TarFile:
        json_data = json.dumps(data.tolist())
        json_buffer = io.BytesIO(json_data.encode("utf-8"))
        tarinfo = TarInfo(
            name=os.path.basename(original_path).replace(original_ext, ".json")
        )
        tarinfo.size = len(json_data.encode("utf-8"))
        tar.addfile(tarinfo, json_buffer)

        return tar
