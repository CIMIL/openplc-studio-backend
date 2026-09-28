from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from plc_platform_backend.modules.modules_models import (
    ModuleParameterSpec,
    ModuleSpec,
    ModuleType,
)
from plc_platform_backend.plugins.plugins_service import get_plugins_service

MODULES_MANIFEST_RESOURCE = Path(__file__).with_name("modules_manifest.yaml")


@lru_cache
def _load_modules_manifest() -> dict[str, list[dict[str, Any]]]:
    try:
        with MODULES_MANIFEST_RESOURCE.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except OSError as error:
        raise OSError(
            f"Could not read the modules manifest resource: {error}"
        ) from error


@lru_cache
def get_modules_repository() -> ModulesRepository:
    _module_repository = ModulesRepository()
    return _module_repository


class ModulesRepository:

    def __init__(self) -> None:
        pass

    def get_all_modules(
        self,
    ) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
        core_modules = _load_modules_manifest()
        return core_modules, self.get_plugin_modules()

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[ModuleSpec]:
        all_modules, plugins = self.get_all_modules()

        modules: list[ModuleSpec] = []

        for module in all_modules[module_type]:
            modules.append(
                ModuleSpec(
                    name=module["name"],
                    settings=self._parse_settings(module),
                    constraints=module.get("constraints") or [],
                )
            )

        if module_type == ModuleType.PLCAlgorithm:
            for module in plugins:
                modules.append(
                    ModuleSpec(
                        name=module["name"],
                        settings=self._parse_settings(module),
                        is_plugin=True,
                    )
                )

        return modules

    @staticmethod
    def _parse_settings(module: dict[str, Any]) -> list[ModuleParameterSpec]:
        return [
            ModuleParameterSpec(**params) for params in module.get("settings") or []
        ]

    def get_plugin_modules(self) -> list[dict[str, Any]]:
        return [spec.model_dump() for spec in get_plugins_service().get_available_specs()]
