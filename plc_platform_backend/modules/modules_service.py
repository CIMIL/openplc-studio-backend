from __future__ import annotations

from functools import lru_cache

from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameter,
    ModuleType,
)
from plc_platform_backend.modules.modules_repository import (
    ModulesRepository,
    get_modules_repository,
)


@lru_cache
def get_modules_service() -> ModuleService:
    _module_service = ModuleService()
    return _module_service


class ModuleService:

    def __init__(self) -> None:
        self.modules_repository: ModulesRepository = get_modules_repository()

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[Module]:
        return self.modules_repository.get_all_modules_by_type(module_type)

    def get_module_params(
        self, module_name: str, module_type: ModuleType
    ) -> list[ModuleParameter]:
        module: Module = self.get_all_modules_by_type(module_type).get(
            module_name, None
        )

        if module is None:
            return []

        return module.settings
