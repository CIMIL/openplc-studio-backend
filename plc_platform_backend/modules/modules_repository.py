from __future__ import annotations

from functools import lru_cache
from types import ModuleType

from plctestbench.loss_simulator import PacketLossSimulator
from plctestbench.output_analyser import OutputAnalyser
from plctestbench.plc_algorithm import PLCAlgorithm
from plctestbench.worker import Worker

from plc_platform_backend.modules.modules_models import ModuleParameters


@lru_cache
def get_modules_repository() -> ModulesRepository:
    _module_repository = ModulesRepository()
    return _module_repository


class ModulesRepository:

    def __init__(self) -> None:
        pass

    def get_all_modules_cls_by_type(self, module_type: ModuleType) -> dict[str, type]:
        module_types: dict[str, type] = self.get_module_types()

        return self.find_subclasses_rec(module_types.get(module_type.name))

    def find_subclasses_rec(self, cls: type) -> dict[str, type]:
        subclasses = cls.__subclasses__()
        module_dict = {cls.__name__: cls for cls in subclasses}
        for subclass in subclasses:
            module_dict.update(self.find_subclasses_rec(subclass))
        return module_dict

    def get_module_types(self) -> dict[str, type]:
        return {cls.__name__: cls for cls in Worker.__subclasses__()}

    def get_module_params(
        self, module_name: str, module_type: str
    ) -> list[ModuleParameters]:
        module_cls: type = self.modules_repository.get_all_modules_cls_by_type(
            module_type
        ).get(module_name)

        module_settings_cls: type = self.get_module_settings_type(module_cls)

        return self.get_module_settings_params(module_settings_cls)
