import inspect
from functools import lru_cache
from typing import Any

from plctestbench.loss_simulator import PacketLossSimulator
from plctestbench.output_analyser import OutputAnalyser
from plctestbench.plc_algorithm import PLCAlgorithm
from plctestbench.worker import Worker


class ModuleService:

    def get_module_params(self, module_name: str, module_type: str) -> dict[str, Any]:
        module_cls: type = self.get_modules_cls(module_type).get(module_name)
        module_settings_cls: type = self.get_module_settings_type(module_cls)
        return self.get_module_settings_params(module_settings_cls)

    def get_modules(self, module_type: str) -> list[str]:
        return list(self.get_modules_cls(module_type).keys())

    def get_module_settings_type(self, module_type: type) -> type:
        return (
            inspect.signature(module_type.__init__)
            .parameters.get("settings")
            .annotation
        )

    def get_module_settings_params(self, module_settings_cls: type) -> dict[str, Any]:
        signature = inspect.signature(module_settings_cls.__init__)
        return {
            name: param.default
            for name, param in signature.parameters.items()
            if name != "self"
        }

    @lru_cache(maxsize=None, typed=True)
    def get_modules_cls(self, module_type: str) -> dict[str, type]:
        module_types: dict[str, type] = self.get_module_types()
        return {
            cls.__name__: cls for cls in module_types.get(module_type).__subclasses__()
        }

    @lru_cache(maxsize=None, typed=True)
    def get_module_types(self) -> dict[str, type]:
        return {cls.__name__: cls for cls in Worker.__subclasses__()}
