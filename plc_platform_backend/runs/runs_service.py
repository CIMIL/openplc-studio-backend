from __future__ import annotations

import io
import json
import os
import pickle
import tarfile
import tempfile
import traceback
from functools import lru_cache

import numpy as np
import plctestbench.loss_simulator
import plctestbench.output_analyser
import plctestbench.plc_algorithm
from plctestbench.models import DBPlatform, TestbenchConfiguration
from plctestbench.output_analyser import SimpleCalculatorData
from plctestbench.plc_testbench import PLCTestbench
from plctestbench.settings import OriginalAudioSettings
from plctestbench.worker import OriginalAudio

from plc_platform_backend import actors
from plc_platform_backend.assets.assets_models import TestbenchNodeDepth
from plc_platform_backend.assets.assets_repository import (
    AssetsRepository,
    get_assets_repository,
)
from plc_platform_backend.assets.assets_service import AssetsService, get_assets_service
from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.modules.modules_models import ModuleType
from plc_platform_backend.runs.runs_models import Run, RunCreateDto, RunStatus
from plc_platform_backend.runs.runs_repository import (
    RunsRepository,
    get_runs_repository,
)


async def _launch_run(
    run: Run, run_repository: RunsRepository, run_service: RunsService
) -> None:
    original_audio_tracks = [
        (OriginalAudio, OriginalAudioSettings(track)) for track in run.tracks
    ]

    packet_loss_simulators = []
    plc_algorithms = []
    output_analysers = []

    for module in run.modules[ModuleType.PacketLossSimulator]:
        cls_ = getattr(plctestbench.loss_simulator, module.name)
        settings_cls = getattr(
            plctestbench.settings,
            run_service.get_module_settings_class_name(module.name),
        )

        packet_loss_simulators.append(
            (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
        )

    for module in run.modules[ModuleType.PLCAlgorithm]:
        cls_ = getattr(plctestbench.plc_algorithm, module.name)
        settings_cls = getattr(
            plctestbench.settings,
            run_service.get_module_settings_class_name(module.name),
        )

        plc_algorithms.append(
            (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
        )

    for module in run.modules[ModuleType.OutputAnalyser]:
        cls_ = getattr(plctestbench.output_analyser, module.name)
        settings_cls = getattr(
            plctestbench.settings,
            run_service.get_module_settings_class_name(module.name),
        )

        output_analysers.append(
            (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
        )

    testbench = PLCTestbench(
        original_audio_tracks,
        packet_loss_simulators,
        plc_algorithms,
        output_analysers,
        run_service.testbench_settings,
    )

    run.status = RunStatus.RUNNING
    run.testbench_internal_id = testbench.run_id
    await run_repository.update_run(run.id, run)

    try:
        testbench.run()
    except Exception as e:
        traceback.print_exception(e)
        run.status = RunStatus.FAILED
        await run_repository.update_run(run.id, run)
        return

    run.status = RunStatus.COMPLETED
    await run_repository.update_run(run.id, run)

    # TODO: notify the frontend that the run is completed


@lru_cache
def get_runs_service() -> RunsService:
    _run_service = RunsService()
    return _run_service


class RunsService:

    def __init__(self) -> None:
        self.runs_repository: RunsRepository = get_runs_repository()
        self.assets_repository: AssetsRepository = get_assets_repository()
        self.assets_service: AssetsService = get_assets_service()
        self.testbench_settings: TestbenchConfiguration = self.get_testbench_settings()

    async def save_run(self, run: RunCreateDto) -> Run:
        saved_run = await self.runs_repository.create_run(run)
        actors.launch_run(run_id=saved_run.id)
        # await self.launch_run_synch(saved_run)
        return Run.from_document(saved_run)

    async def find_by_id(self, run_id: str) -> Run:
        return Run.from_document(await self.runs_repository.get_run(run_id))

    async def get_all(self) -> list[Run]:
        return [Run.from_document(run) for run in await self.runs_repository.get_all()]

    async def launch_run_synch(self, run: Run) -> Run:
        await _launch_run(run, self.runs_repository, self)

    async def get_assets_tar_by_depth(
        self, run_id: str, depth: TestbenchNodeDepth
    ) -> list[str]:
        run: Run = await self.find_by_id(run_id)

        paths = self.assets_repository.get_assets_paths(
            run, depth, self.testbench_settings
        )
        paths = [self.assets_repository.resolve_asset_path(p, depth) for p in paths]

        tar_buffer = io.BytesIO()

        with tarfile.open(
            fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT
        ) as tar:
            for p in paths:
                if not os.path.exists(p):
                    continue

                if depth == TestbenchNodeDepth.SAMPLE_MASKS:
                    data: np.ndarray = np.load(p, allow_pickle=True)
                    tar = self.assets_service.add_json_to_tar(data, tar, p, ".npy")
                elif depth == TestbenchNodeDepth.OUTPUT_ANALYSIS:
                    with open(p, "rb") as pkl:
                        data: np.ndarray = pickle.load(pkl).get_error()
                    tar = self.assets_service.add_json_to_tar(data, tar, p, ".pickle")
                else:
                    tar.add(p, arcname=self.strip_asset_filenames(p, depth))

        tar_buffer.seek(0)
        return tar_buffer

    def get_testbench_settings(self) -> TestbenchConfiguration:
        config = get_configuration()

        testbench_settings = TestbenchConfiguration(
            root_folder=config.plc_root_folder,
            db_platform=DBPlatform.MONGODB,
            db_ip="mongo",
            db_port="27017",
            db_username=config.mongo_initdb_root_username,
            db_password=config.mongo_initdb_root_password,
        )

        return testbench_settings

    def get_module_settings_class_name(self, module: str) -> str:
        return f"{module}Settings"

    def strip_asset_filenames(self, path, depth):
        items = path.split("/")[2:]
        print(tuple(items))
        if depth == TestbenchNodeDepth.ORIGINAL_TRACKS:
            (original_track,) = tuple(items)
            return "/".join([original_track])
        if depth == TestbenchNodeDepth.RECONSTRUCTED_TRACKS:
            original_track, sample_mask, reconstructed_track = tuple(items)
            original_track = original_track.split("-")[0]
            sample_mask = sample_mask.split("-")[0]
            reconstructed_track = ".".join(
                [reconstructed_track.split("-")[0], reconstructed_track.split(".")[-1]]
            )
            return "/".join([original_track, sample_mask, reconstructed_track])
