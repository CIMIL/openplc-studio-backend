from __future__ import annotations

import os
import pathlib
from functools import lru_cache

from plc_platform_backend.commons.configuration.configuration import get_configuration


@lru_cache
def get_files_repository() -> FilesRepository:
    _file_repository = FilesRepository()
    return _file_repository


class FilesRepository:

    def __init__(self) -> None:
        pass

    async def save_file(self, content: bytes, filename: str) -> None:
        path = pathlib.Path(self.get_original_track_basepath(), filename)

        with open(path, "wb") as f:
            f.write(content)

    async def get_original_track_file(self, filename: str):
        path = pathlib.Path(self.get_original_track_basepath(), filename)

        return open(path, "rb")

    async def get_all_original_track_filenames(self) -> list[str]:
        tracks_basepath = self.get_original_track_basepath()
        return [
            f
            for f in os.listdir(tracks_basepath)
            if os.path.isfile(os.path.join(tracks_basepath, f))
        ]

    def get_original_track_basepath(self) -> pathlib.Path:
        root_folder = get_configuration().plc_root_folder
        root_folder = pathlib.Path(root_folder).resolve()
        return root_folder
