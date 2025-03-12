from __future__ import annotations

from functools import lru_cache
from tempfile import SpooledTemporaryFile

from plc_platform_backend.files.files_repository import (
    FilesRepository,
    get_files_repository,
)


@lru_cache
def get_files_service() -> FilesService:
    _file_service = FilesService()
    return _file_service


class FilesService:

    def __init__(self) -> None:
        self.files_repository: FilesRepository = get_files_repository()

    async def save_file(self, data: bytes, filename: str) -> None:
        await self.files_repository.save_file(data, filename)

    async def get_all_original_track_filenames(self) -> list[str]:
        return await self.files_repository.get_all_original_track_filenames()
