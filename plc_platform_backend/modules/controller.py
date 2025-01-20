from typing import Annotated, Any

from fastapi import APIRouter, Depends

from plc_platform_backend.modules.service import ModuleService

router = APIRouter(
    prefix="/module",
    tags=["module"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_modules(
    module_type: str, module_service: Annotated[ModuleService, Depends()]
) -> list[str]:
    return module_service.get_modules(module_type)


@router.get("/{module_type}/parameters")
async def get_module_parameters(
    module_name: str,
    module_type: str,
    module_service: Annotated[ModuleService, Depends()],
) -> dict[str, Any]:
    return module_service.get_module_params(module_name, module_type)
