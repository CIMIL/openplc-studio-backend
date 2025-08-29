from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from plc_platform_backend.assets.assets_service import AssetsService, get_assets_service
from plc_platform_backend.commons.configuration.configuration import get_configuration

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
    assets: list[UploadFile],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
):
    for file in assets:
        await assets_service.save_file(await file.read(), file.filename)
    return await assets_service.get_all_original_track_filenames()


@router.get("/original-tracks")
async def get_track_filenames(
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> list[str]:
    return await assets_service.get_all_original_track_filenames()


# @router.get("/reconstructed-tracks")
# async def get_reconstructed_track_filenames_by_run(
#     run_id: str,
#     assets_service: Annotated[FilesService, Depends(get_assets_service)],
# ) -> list[str]:
#     pass
#     # return await assets_service.get_all_original_track_filenames()
