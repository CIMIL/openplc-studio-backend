from __future__ import annotations

from functools import lru_cache

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
