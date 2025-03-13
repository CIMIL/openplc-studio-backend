from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.files.files_service import FilesService, get_files_service

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "",
    status_code=201,
)
async def upload_files(
    files: list[UploadFile],
    files_service: Annotated[FilesService, Depends(get_files_service)],
):
    for file in files:
        await files_service.save_file(await file.read(), file.filename)
    return await files_service.get_all_original_track_filenames()


@router.get("/names")
async def get_filenames(
    files_service: Annotated[FilesService, Depends(get_files_service)],
) -> list[str]:
    return await files_service.get_all_original_track_filenames()
