from typing import Annotated, Any

from fastapi import APIRouter, Depends

from plc_platform_backend.modules.models import Module, ModuleParameters, ModuleType
from plc_platform_backend.modules.service import ModuleService

router = APIRouter(
    prefix="/modules",
    tags=["modules"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_modules(
    module_type: ModuleType, module_service: Annotated[ModuleService, Depends()]
) -> list[Module]:
    return module_service.get_modules(module_type)


@router.get("/{module_type}/parameters")
async def get_module_parameters(
    module_name: str,
    module_type: ModuleType,
    module_service: Annotated[ModuleService, Depends()],
) -> list[ModuleParameters]:
    return module_service.get_module_params(module_name, module_type)
