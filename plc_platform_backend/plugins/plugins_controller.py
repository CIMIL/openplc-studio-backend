from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from plc_platform_backend.plugins.plugins_models import PluginInventory
from plc_platform_backend.plugins.plugins_service import PluginsService, get_plugins_service

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=PluginInventory)
def get_plugins(
    plugins_service: Annotated[PluginsService, Depends(get_plugins_service)],
) -> PluginInventory:
    try:
        return plugins_service.scan()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
