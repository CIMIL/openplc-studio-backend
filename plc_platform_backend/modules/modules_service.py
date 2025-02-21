from __future__ import annotations

import inspect
from enum import Enum
from functools import lru_cache
from typing import Any, get_args

from plctestbench.loss_simulator import PacketLossSimulator
from plctestbench.output_analyser import OutputAnalyser
from plctestbench.plc_algorithm import PLCAlgorithm
from plctestbench.worker import Worker

from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameters,
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

    def get_module_params(
        self, module_name: str, module_type: str
    ) -> list[ModuleParameters]:
        module_cls: type = self.modules_repository.get_all_modules_cls_by_type(
            module_type
        ).get(module_name)

        module_settings_cls: type = self.get_module_settings_type(module_cls)

        return self.get_module_settings_params(module_settings_cls)

    def get_all_modules_by_type(self, module_type: ModuleType) -> list[Module]:
        module_cls: list[tuple[str, type]] = list(
            self.modules_repository.get_all_modules_cls_by_type(module_type).items()
        )

        module_settings_cls: list[type] = [
            self.get_module_settings_type(cls_type) for _, cls_type in module_cls
        ]

        modules_list: list[Module] = [
            Module(name=module, settings=self.get_module_settings_params(settings))
            for (module, _), settings in zip(module_cls, module_settings_cls)
        ]

        return modules_list

    def get_module_settings_type(self, module_cls: type) -> type:
        return (
            inspect.signature(module_cls.__init__).parameters.get("settings").annotation
        )

    def get_module_settings_params(
        self, module_settings_cls: type
    ) -> list[ModuleParameters]:
        signature: inspect.Signature = inspect.signature(module_settings_cls.__init__)

        constructor_params: list[ModuleParameters] = []
        for name, param in signature.parameters.items():
            if name == "self":
                continue

            values: list[Any] = None

            param_type: str = param.annotation.__name__

            param_default: Any = param.default

            try:
                if issubclass(param.annotation, Enum):
                    param_type = Enum.__name__
                    param_default = param_default.value
                    values = [value.value for value in param.annotation]
            except Exception as e:
                print(f"Error processing parameter {param}: {str(e)}")

            if param.annotation.__name__ == "list":
                inner_type = get_args(param.annotation)[0].__name__
                param_type = f"{param_type}_{inner_type}"

            constructor_params.append(
                ModuleParameters(
                    name=name,
                    type=param_type,
                    default=param_default,
                    value=param_default,
                    values=values,
                )
            )
        return constructor_params
