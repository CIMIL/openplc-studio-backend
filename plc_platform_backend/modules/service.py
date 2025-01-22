import inspect
from functools import lru_cache
from typing import Any

from numpy import sign
from plctestbench.loss_simulator import PacketLossSimulator
from plctestbench.output_analyser import OutputAnalyser
from plctestbench.plc_algorithm import PLCAlgorithm
from plctestbench.worker import Worker

from plc_platform_backend.modules.models import Module, ModuleParameters, ModuleType


class ModuleService:

    def get_module_params(
        self, module_name: str, module_type: str
    ) -> list[ModuleParameters]:
        module_cls: type = self.get_modules_cls(module_type).get(module_name)

        module_settings_cls: type = self.get_module_settings_type(module_cls)

        return self.get_module_settings_params(module_settings_cls)

    def get_modules(self, module_type: ModuleType) -> list[Module]:
        module_cls: list[tuple[str, type]] = list(
            self.get_modules_cls(module_type).items()
        )

        module_settings_cls: list[type] = [
            self.get_module_settings_type(cls_type) for _, cls_type in module_cls
        ]

        return [
            {"name": module, "settings": self.get_module_settings_params(settings)}
            for (module, _), settings in zip(module_cls, module_settings_cls)
        ]

    def get_module_settings_type(self, module_cls: type) -> type:
        return (
            inspect.signature(module_cls.__init__).parameters.get("settings").annotation
        )

    def get_module_settings_params(
        self, module_settings_cls: type
    ) -> list[dict[str, Any]]:
        signature = inspect.signature(module_settings_cls.__init__)

        return [
            {"name": name, "type": param.annotation.__name__, "default": param.default}
            for name, param in signature.parameters.items()
            if name != "self"
        ]

    @lru_cache(maxsize=None, typed=True)
    def get_modules_cls(self, module_type: ModuleType) -> dict[str, type]:
        module_types: dict[str, type] = self.get_module_types()

        return {
            cls.__name__: cls
            for cls in module_types.get(module_type.name).__subclasses__()
        }

    @lru_cache(maxsize=None, typed=True)
    def get_module_types(self) -> dict[str, type]:
        return {cls.__name__: cls for cls in Worker.__subclasses__()}
