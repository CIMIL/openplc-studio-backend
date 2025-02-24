from __future__ import annotations

from functools import lru_cache
from typing import Any

import plctestbench

from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameter,
    ModuleType,
)


@lru_cache
def get_modules_repository() -> ModulesRepository:
    _module_repository = ModulesRepository()
    return _module_repository


class ModulesRepository:

    def __init__(self) -> None:
        pass

    def get_all_modules(self) -> dict[str, list[dict[str, Any]]]:
        return plctestbench.get_available_modules()

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[Module]:
        all_modules = self.get_all_modules()

        modules: list[Module] = []

        for module in all_modules[module_type]:
            parameters: list[ModuleParameter] = [
                ModuleParameter(**params) for params in module.get("settings") or []
            ]

            modules.append(Module(name=module["name"], settings=parameters))

        return modules
