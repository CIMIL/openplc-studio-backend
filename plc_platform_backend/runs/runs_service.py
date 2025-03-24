from __future__ import annotations

from functools import lru_cache

import plctestbench.loss_simulator
import plctestbench.output_analyser
import plctestbench.plc_algorithm
from plctestbench.models import DBPlatform, TestbenchConfiguration
from plctestbench.plc_testbench import PLCTestbench
from plctestbench.settings import OriginalAudioSettings
from plctestbench.worker import OriginalAudio

from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.modules.modules_models import ModuleType
from plc_platform_backend.runs.runs_models import Run
from plc_platform_backend.runs.runs_repository import (
    RunsRepository,
    get_runs_repository,
)


@lru_cache
def get_runs_service() -> RunsService:
    _run_service = RunsService()
    return _run_service


class RunsService:

    def __init__(self) -> None:
        self.runs_repository: RunsRepository = get_runs_repository()

    async def save_run(self, run: Run) -> Run:
        saved_run = await self.runs_repository.create_run(run)
        await self.launch_run(saved_run)
        return Run.from_document(saved_run)

    async def find_by_id(self, run_id: str) -> Run:
        return Run.from_document(await self.runs_repository.get_run(run_id))

    async def get_all(self) -> list[Run]:
        return [Run.from_document(run) for run in await self.runs_repository.get_all()]

    async def launch_run(self, run: Run) -> Run:
        original_audio_tracks = [
            (OriginalAudio, OriginalAudioSettings(track)) for track in run.tracks
        ]

        packet_loss_simulators = []
        plc_algorithms = []
        output_analysers = []

        for module in run.modules[ModuleType.PacketLossSimulator]:
            cls_ = getattr(plctestbench.loss_simulator, module.name)
            settings_cls = getattr(
                plctestbench.settings, self.get_module_settings_class_name(module.name)
            )

            packet_loss_simulators.append(
                (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
            )

        for module in run.modules[ModuleType.PLCAlgorithm]:
            cls_ = getattr(plctestbench.plc_algorithm, module.name)
            settings_cls = getattr(
                plctestbench.settings, self.get_module_settings_class_name(module.name)
            )

            plc_algorithms.append(
                (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
            )

        for module in run.modules[ModuleType.OutputAnalyser]:
            cls_ = getattr(plctestbench.output_analyser, module.name)
            settings_cls = getattr(
                plctestbench.settings, self.get_module_settings_class_name(module.name)
            )

            output_analysers.append(
                (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
            )

        testbench = PLCTestbench(
            original_audio_tracks,
            packet_loss_simulators,
            plc_algorithms,
            output_analysers,
            self.get_testbench_settings(),
        )

        testbench.run()

        testbench.data_manager

    def get_testbench_settings(self) -> TestbenchConfiguration:
        config = get_configuration()

        testbench_settings = TestbenchConfiguration(
            root_folder=config.plc_root_folder,
            db_platform=DBPlatform.TINYDB,
        )

        return testbench_settings

    def get_module_settings_class_name(self, module: str) -> str:
        return f"{module}Settings"
