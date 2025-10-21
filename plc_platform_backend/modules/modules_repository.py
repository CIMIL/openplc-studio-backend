from __future__ import annotations

import ast
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import plctestbench
import yaml
from plctestbench.plc_algorithm import PLCAlgorithm

from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.modules.modules_models import (
    ModuleParameterSpec,
    ModuleSpec,
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
        core_modules = plctestbench.get_available_modules()
        plugins = self.get_plugin_modules()
        return core_modules, plugins

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[ModuleSpec]:
        all_modules, plugins = self.get_all_modules()

        modules: list[ModuleSpec] = []

        for module in all_modules[module_type]:
            parameters: list[ModuleParameterSpec] = [
                ModuleParameterSpec(**params) for params in module.get("settings") or []
            ]

            modules.append(ModuleSpec(name=module["name"], settings=parameters))

        if module_type == ModuleType.PLCAlgorithm:
            for module in plugins:
                parameters: list[ModuleParameterSpec] = [
                    ModuleParameterSpec(**params)
                    for params in module.get("settings") or []
                ]

                modules.append(ModuleSpec(name=module["name"], settings=parameters))

        return modules

    def get_plugin_modules(self):
        plugins_path = Path(get_configuration().plugins_directory)

        plugins = []

        plugin_files = [f for f in os.listdir(plugins_path) if f.endswith(".py")]

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
