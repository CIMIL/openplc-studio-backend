from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from plc_platform_backend.assets.assets_models import OriginalTrackMetadata
from plc_platform_backend.assets.assets_service import AssetsService, get_assets_service

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "",
    status_code=201,
)
async def upload_assets(
    files: list[UploadFile],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
):
    for file in files:
        await assets_service.save_file(await file.read(), file.filename)
    return await assets_service.get_all_original_track_filenames()


@router.get(
    "/original-tracks",
)
async def get_original_tracks(
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
):
    return await assets_service.get_all_original_track_filenames()


@router.get(
    "/original-tracks/metadata",
)
async def get_original_tracks_metadata(
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> list[OriginalTrackMetadata]:
    return await assets_service.get_all_original_track_metadata()
