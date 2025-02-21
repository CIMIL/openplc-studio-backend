from typing import Annotated

from fastapi import APIRouter, Depends

from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameters,
    ModuleType,
)
from plc_platform_backend.modules.modules_service import (
    ModuleService,
    get_modules_service,
)

router = APIRouter(
    prefix="/modules",
    tags=["modules"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_modules(
    module_type: ModuleType,
    modules_service: Annotated[ModuleService, Depends(get_modules_service)],
) -> list[Module]:
    return modules_service.get_all_modules_by_type(module_type)


@router.get("/{module_type}/parameters")
async def get_module_parameters(
    module_name: str,
    module_type: ModuleType,
    modules_service: Annotated[ModuleService, Depends(get_modules_service)],
) -> list[ModuleParameters]:
    return modules_service.get_module_params(module_name, module_type)
