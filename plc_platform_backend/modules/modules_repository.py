from __future__ import annotations

import ast
import os
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.modules.modules_models import (
    ModuleParameterSpec,
    ModuleSpec,
    ModuleType,
)

MODULES_MANIFEST_RESOURCE = files("plc_platform_backend.modules").joinpath("modules_manifest.yaml")


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
        plugins = self.get_plugin_modules()
        return core_modules, plugins

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
                    )
                )

        return modules

    @staticmethod
    def _parse_settings(module: dict[str, Any]) -> list[ModuleParameterSpec]:
        return [
            ModuleParameterSpec(**params) for params in module.get("settings") or []
        ]

    def get_plugin_modules(self) -> list[dict[str, Any]]:
        plugins_path = Path(get_configuration().plugins_directory)

        plugins: list[dict[str, Any]] = []

        try:
            plugin_files = [f for f in os.listdir(plugins_path) if f.endswith(".py")]
        except OSError as error:
            print(f"Error listing plugins in {plugins_path}: {error}")
            return plugins

        for plugin_file in plugin_files:
            try:
                with open(plugins_path / plugin_file, "r") as f:
                    content = f.read()

                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)

                if not docstring:
                    continue

                yaml_data = yaml.safe_load(docstring)

                if yaml_data and isinstance(yaml_data, list) and len(yaml_data) > 0:
                    plugin_config = yaml_data[0]
                    plugins.append(plugin_config)

            except Exception as e:
                print(f"Error parsing plugin {plugin_file}: {e}")
                continue

        return plugins