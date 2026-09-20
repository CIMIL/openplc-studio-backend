from __future__ import annotations

from functools import lru_cache

from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameterSpec,
    ModuleSpec,
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

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[ModuleSpec]:
        return self.modules_repository.get_all_modules_by_type(module_type)

    def get_module_spec(
        self, module_name: str, module_type: ModuleType
    ) -> ModuleSpec | None:
        return next(
            (
                module
                for module in self.get_all_modules_by_type(module_type)
                if module.name == module_name
            ),
            None,
        )

    def get_module_params(
        self, module_name: str, module_type: ModuleType
    ) -> list[ModuleParameterSpec]:
        module = self.get_module_spec(module_name, module_type)

        if module is None:
            return []

        return module.settings
