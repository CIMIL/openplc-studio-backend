from __future__ import annotations

import asyncio
import io
import json
import logging
import pickle
import tarfile
import threading
import traceback
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import plctestbench.loss_simulator
import plctestbench.output_analyser
import plctestbench.plc_algorithm
import redis.asyncio as aioredis
from plctestbench.models import DBPlatform, TestbenchConfiguration
from plctestbench.output_analyser import PEAQData, SimpleCalculatorData
from plctestbench.plc_testbench import PLCTestbench
from plctestbench.settings import CrossfadeSettings, OriginalAudioSettings
from plctestbench.utils import get_class
from plctestbench.worker import OriginalAudio

from plc_platform_backend import actors
from plc_platform_backend.assets.assets_models import RunArtifactKind, TestbenchNodeDepth
from plc_platform_backend.assets.assets_repository import (
    AssetsRepository,
    get_assets_repository,
)
from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.commons.interceptable_tqdm import InterceptableTqdm
from plc_platform_backend.commons.redis_client import get_redis_client
from plc_platform_backend.modules.modules_models import (
    Module,
    ModuleParameter,
    ModuleType,
)
from plc_platform_backend.modules.modules_validator import ModuleConfigValidator
from plc_platform_backend.runs.runs_models import (
    NodeProgress,
    Run,
    RunCompletionMessage,
    RunCreateDto,
    RunPage,
    RunProgressMessage,
    RunSortField,
    RunStateChangeMessage,
    RunStatus,
    SortDirection,
)
from plc_platform_backend.runs.runs_repository import (
    RunsRepository,
    get_runs_repository,
)
from plc_platform_backend.runs.runs_ws import (
    RUN_COMPLETION_CHANNEL,
    RUN_PROGRESS_CHANNEL,
    RUN_STATE_CHANGE_CHANNEL,
)

from plc_platform_backend.modules.modules_service import ModuleService
from plc_platform_backend.runs.runs_models import (
    RunConfigDto,
    RunConfigValidationError,
)

_PROGRESS_POLL_INTERVAL = 0.1
logger = logging.getLogger(__name__)

_ARTIFACT_DEPTHS = {
    RunArtifactKind.ORIGINAL_TRACKS: TestbenchNodeDepth.ORIGINAL_TRACKS,
    RunArtifactKind.SAMPLE_MASKS: TestbenchNodeDepth.SAMPLE_MASKS,
    RunArtifactKind.RECONSTRUCTED_TRACKS: TestbenchNodeDepth.RECONSTRUCTED_TRACKS,
    RunArtifactKind.OUTPUT_ANALYSIS: TestbenchNodeDepth.OUTPUT_ANALYSIS,
}


@dataclass(frozen=True)
class RunArtifact:
    source_path: Path
    archive_path: str
    encoding: Literal["file", "numpy-json", "output-analysis-json"]


class RunNotDeletableError(Exception):
    pass


class RunNotExecutableError(Exception):
    pass


class RunQueueError(Exception):
    pass


class RunPreparationError(Exception):
    pass


class RunArtifactsUnavailableError(Exception):
    pass


class RunArtifactsNotFoundError(Exception):
    def __init__(self, archive_paths: list[str]) -> None:
        self.archive_paths = archive_paths
        super().__init__("Run artifacts were not found: " + ", ".join(archive_paths))


class RunArtifactConversionError(Exception):
    pass


def _seed_progress_state(testbench: PLCTestbench) -> dict[str, NodeProgress]:
    """
    Walks every node of every tree in the run and seeds an entry for it,
    so nodes that haven't started yet (and nodes that finish between two
    polls) still show up in every RunProgressMessage.
    """
    progress_state: dict[str, NodeProgress] = {}
    for root_node in testbench.data_manager.root_nodes:
        levels = testbench.get_nodes_by_depth(root_node)
        for nodes in levels.values():
            for node in nodes:
                node_id = node.get_id()
                progress_state[node_id] = NodeProgress(
                    description=str(node.get_worker()),
                    node_id=node_id,
                    current=0,
                    total=None,
                )
    return progress_state


def _get_module_parameter(settings, parameter):
    return [s.value for s in settings if s.name == parameter][0]


def _hydrate_crossfade_settings(crossfade_list: list) -> list[CrossfadeSettings]:
    """Idrata una lista di crossfade settings da dizionari a oggetti CrossfadeSettings"""
    result = []
    for xf in crossfade_list:
        crossfade_settings_cls = getattr(plctestbench.settings, xf["name"])
        result.append(
            crossfade_settings_cls(
                **{xfs["name"]: xfs["value"] for xfs in xf["settings"]}
            )
        )
    return result


def _get_hydrated_module_settings(
    settings: list[ModuleParameter], run_service: RunsService
):
    hydrated_module_settings = []
    for s in settings:
        advanced_plc_band_settings: dict[
            str, list[plctestbench.plc_algorithm.PLCAlgorithm]
        ] = {}
        advanced_plc_frequencies: dict[str, list[int]] = {}
        if s.name == "crossfade":
            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=_hydrate_crossfade_settings(s.value))
            )
        elif s.name == "fade_in":
            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=_hydrate_crossfade_settings(s.value))
            )
        elif s.name == "crossfade_frequencies" and s.value:
            try:
                crossfade_frequencies = [int(f) for f in s.value]
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid crossfade frequencies: {s.value}") from error
            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=crossfade_frequencies)
            )
        elif s.name == "crossover_order" and s.value:
            try:
                crossover_order = int(s.value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid crossover order: {s.value}") from error
            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=crossover_order)
            )
        elif s.name == "band_settings":
            for band in {"linked", "mid", "side", "left", "right"}:
                if band not in s.value.keys():
                    continue

                stereo_image_processing = _get_module_parameter(
                    settings, "stereo_image_processing"
                )
                channel_link = _get_module_parameter(settings, "channel_link")

                if stereo_image_processing == "dual_mono" and band not in {
                    "left",
                    "right",
                }:
                    continue

                if stereo_image_processing == "mid_side" and band not in {
                    "mid",
                    "side",
                }:
                    continue

                if channel_link and band != "linked":
                    continue

                advanced_plc_band_settings[band] = []
                for algorithm in s.value[band]:
                    algorithm_settings_cls = getattr(
                        plctestbench.settings,
                        run_service.get_module_settings_class_name(algorithm["name"]),
                    )
                    hydrated_algorithm_settings = _get_hydrated_module_settings(
                        [
                            ModuleParameter(name=as_["name"], value=as_["value"])
                            for as_ in algorithm["settings"]
                        ],
                        run_service,
                    )
                    advanced_plc_band_settings[band].append(
                        algorithm_settings_cls(
                            **{
                                has.name: has.value
                                for has in hydrated_algorithm_settings
                            }
                        )
                    )

            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=advanced_plc_band_settings)
            )
        elif s.name == "frequencies":
            for band in ["linked", "mid", "side", "left", "right"]:
                if band not in s.value.keys():
                    continue

                stereo_image_processing = _get_module_parameter(
                    settings, "stereo_image_processing"
                )
                channel_link = _get_module_parameter(settings, "channel_link")

                if stereo_image_processing == "dual_mono" and band not in {
                    "left",
                    "right",
                }:
                    continue

                if stereo_image_processing == "mid_side" and band not in {
                    "mid",
                    "side",
                }:
                    continue

                if channel_link and band != "linked":
                    continue

                advanced_plc_frequencies[band] = [f for f in s.value[band]]

            hydrated_module_settings.append(
                ModuleParameter(name=s.name, value=advanced_plc_frequencies)
            )
        else:
            hydrated_module_settings.append(s)

    return hydrated_module_settings


async def _publish_run_completion(
    run_id: str, run_name: str, success: bool, redis_client: aioredis.Redis
) -> None:
    message = RunCompletionMessage(run_id=run_id, run_name=run_name, success=success)
    await redis_client.publish(RUN_COMPLETION_CHANNEL, message.model_dump_json())


async def _publish_run_progress(
    run_id: str, run_name: str, nodes: list[NodeProgress], redis_client: aioredis.Redis
) -> None:
    message = RunProgressMessage(run_id=run_id, run_name=run_name, nodes=nodes)
    await redis_client.publish(RUN_PROGRESS_CHANNEL, message.model_dump_json())


async def _publish_run_state_change(
    run_id: str,
    run_name: str,
    previous_status: RunStatus,
    new_status: RunStatus,
    redis_client: aioredis.Redis,
) -> None:
    message = RunStateChangeMessage(
        run_id=run_id,
        run_name=run_name,
        previous_status=previous_status,
        new_status=new_status,
    )
    await redis_client.publish(RUN_STATE_CHANGE_CHANNEL, message.model_dump_json())


async def _transition_run_status(
    run_id: str,
    run_name: str,
    expected_status: RunStatus,
    new_status: RunStatus,
    run_repository: RunsRepository,
    redis_client: aioredis.Redis,
):
    transitioned_document = await run_repository.transition_status(
        run_id, expected_status, new_status
    )
    if transitioned_document is None:
        return None

    try:
        await _publish_run_state_change(
            run_id,
            run_name,
            expected_status,
            new_status,
            redis_client,
        )
    except Exception:
        logger.exception(
            "Could not publish state change for run %s (%s -> %s)",
            run_id,
            expected_status.value,
            new_status.value,
        )

    return transitioned_document


def _build_testbench_from_config(
    run: Run | RunCreateDto,
    run_service: RunsService,
) -> PLCTestbench:
    original_audio_tracks = [
        (OriginalAudio, OriginalAudioSettings(track)) for track in run.tracks
    ]

    packet_loss_simulators = []
    plc_algorithms = []
    output_analysers = []

    for module in run.modules[ModuleType.PacketLossSimulator]:
        cls_ = get_class(module.name)
        settings_cls = get_class(
            run_service.get_module_settings_class_name(module.name)
        )

        packet_loss_simulators.append(
            (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
        )

    for module in run.modules[ModuleType.PLCAlgorithm]:
        cls_ = get_class(module.name)
        settings_cls = get_class(
            run_service.get_module_settings_class_name(module.name)
        )

        hydrated_module_settings = _get_hydrated_module_settings(
            module.settings, run_service
        )

        plc_algorithms.append(
            (cls_, settings_cls(**{s.name: s.value for s in hydrated_module_settings}))
        )

    for module in run.modules[ModuleType.OutputAnalyser]:
        cls_ = get_class(module.name)
        settings_cls = get_class(
            run_service.get_module_settings_class_name(module.name)
        )

        output_analysers.append(
            (cls_, settings_cls(**{s.name: s.value for s in module.settings}))
        )

    testbench_settings = run_service.testbench_settings
    testbench_settings.progress_monitor = lambda caller: InterceptableTqdm

    testbench = PLCTestbench(
        original_audio_tracks,
        packet_loss_simulators,
        plc_algorithms,
        output_analysers,
        run_service.testbench_settings,
    )

    # Store each generated execution-node ID on its configured module while the
    # tree is prepared. The progress page can therefore render before execution.
    pls_modules = run.modules[ModuleType.PacketLossSimulator]
    plc_modules = run.modules[ModuleType.PLCAlgorithm]
    oa_modules = run.modules[ModuleType.OutputAnalyser]

    n_pls = len(pls_modules)
    n_plc = len(plc_modules)

    for module in (*pls_modules, *plc_modules, *oa_modules):
        module.node_ids = []

    for root_node in testbench.data_manager.root_nodes:
        testbench_nodes = testbench.get_nodes_by_depth(root_node)
        pls_nodes = testbench_nodes[1]
        plc_nodes = testbench_nodes[2]
        oa_nodes = testbench_nodes[3]

        for module, node in zip(pls_modules, pls_nodes):
            module.node_ids.append(node.get_id())

        for index, module in enumerate(plc_modules):
            start = index * n_pls
            module.node_ids += [
                node.get_id() for node in plc_nodes[start : start + n_pls]
            ]

        oa_step = n_pls * n_plc
        for index, module in enumerate(oa_modules):
            start = index * oa_step
            module.node_ids += [
                node.get_id() for node in oa_nodes[start : start + oa_step]
            ]

    run.testbench_internal_id = testbench.run_id
    run.status = RunStatus.CREATED
    return testbench


async def _launch_run(
    run: Run,
    run_repository: RunsRepository,
    run_service: RunsService,
    redis_client: aioredis.Redis,
) -> None:
    running_document = await _transition_run_status(
        run.id,
        run.name,
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        run_repository,
        redis_client,
    )
    if running_document is None:
        return

    run = Run.from_document(running_document)

    try:
        if not run.testbench_internal_id:
            raise ValueError(f"Run {run.id} has not been prepared")

        testbench_settings = run_service.testbench_settings
        testbench_settings.progress_monitor = lambda caller: InterceptableTqdm
        testbench = PLCTestbench(
            testbench_settings=testbench_settings,
            run_id=run.testbench_internal_id,
        )
        progress_state = _seed_progress_state(testbench)
        run_exception: Exception | None = None

        def _run_thread() -> None:
            nonlocal run_exception
            try:
                testbench.run()
            except Exception as error:
                run_exception = error
            finally:
                InterceptableTqdm.reset_all()

        thread = threading.Thread(target=_run_thread, daemon=True)
        thread.start()

        while thread.is_alive():
            active = InterceptableTqdm.get_all()
            closed = InterceptableTqdm.get_all_closed()

            for description, current, total in (
                progress_bar.get_progress() for progress_bar in active.values()
            ):
                if "|" not in description:
                    continue
                description, _, node_id = description.partition("|")
                if not node_id:
                    continue
                progress_state[node_id] = NodeProgress(
                    description=description,
                    node_id=node_id,
                    current=current,
                    total=total,
                )

            for node_id, (description, current, total) in closed.items():
                if "|" in description:
                    description = description.split("|", 1)[0]
                progress_state[node_id] = NodeProgress(
                    description=description,
                    node_id=node_id,
                    current=current,
                    total=total,
                )

            await _publish_run_progress(
                run.id,
                run.name,
                list(progress_state.values()),
                redis_client,
            )
            await asyncio.sleep(_PROGRESS_POLL_INTERVAL)

        thread.join()
        if run_exception is not None:
            raise run_exception
    except Exception as error:
        traceback.print_exception(error)
        await _transition_run_status(
            run.id,
            run.name,
            RunStatus.RUNNING,
            RunStatus.FAILED,
            run_repository,
            redis_client,
        )
        await _publish_run_completion(
            run.id, run.name, success=False, redis_client=redis_client
        )
        return
    finally:
        InterceptableTqdm.reset_all()

    await _transition_run_status(
        run.id,
        run.name,
        RunStatus.RUNNING,
        RunStatus.COMPLETED,
        run_repository,
        redis_client,
    )
    await _publish_run_completion(
        run.id, run.name, success=True, redis_client=redis_client
    )


@lru_cache
def get_runs_service() -> RunsService:
    _run_service = RunsService()
    return _run_service


class RunsService:
    def __init__(self) -> None:
        self.runs_repository: RunsRepository = get_runs_repository()
        self.assets_repository: AssetsRepository = get_assets_repository()
        self.testbench_settings: TestbenchConfiguration = self.get_testbench_settings()
        self.redis_client: aioredis.Redis = get_redis_client()

    async def save_run(self, run: RunCreateDto) -> Run:
        run.status = RunStatus.CREATED
        run.testbench_internal_id = None
        try:
            _build_testbench_from_config(run, self)
        except Exception as error:
            raise RunPreparationError(str(error)) from error

        saved_run = await self.runs_repository.create_run(run)
        return Run.from_document(saved_run)

    async def execute_run(self, run_id: str) -> Run:
        run = await self.find_by_id(run_id)
        if not run.testbench_internal_id:
            raise RunNotExecutableError(f"Run {run_id} has not been prepared")

        queued_document = await _transition_run_status(
            run_id,
            run.name,
            RunStatus.CREATED,
            RunStatus.QUEUED,
            self.runs_repository,
            self.redis_client,
        )
        if queued_document is None:
            current_run = await self.find_by_id(run_id)
            raise RunNotExecutableError(
                f"Run {run_id} cannot be executed while its status is "
                f"{current_run.status.value}"
            )

        try:
            actors.launch_run.send(run_id=run_id)
        except Exception as error:
            await _transition_run_status(
                run_id,
                run.name,
                RunStatus.QUEUED,
                RunStatus.CREATED,
                self.runs_repository,
                self.redis_client,
            )
            raise RunQueueError(f"Run {run_id} could not be queued") from error

        return Run.from_document(queued_document)

    async def find_by_id(self, run_id: str) -> Run:
        document = await self.runs_repository.get_run(run_id)
        if document is None:
            raise ValueError(f"Run {run_id} not found")
        return Run.from_document(document)

    async def get_page(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        statuses: list[RunStatus] | None = None,
        sort_by: RunSortField = "created",
        sort_direction: SortDirection = "desc",
    ) -> RunPage:
        total = await self.runs_repository.count_all(search, statuses)
        skip = (page - 1) * page_size
        documents = await self.runs_repository.get_page(
            skip,
            page_size,
            search,
            statuses,
            sort_by,
            sort_direction,
        )
        return RunPage(
            items=[Run.from_document(document) for document in documents],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete_run(self, run_id: str) -> None:
        run = await self.find_by_id(run_id)
        if run.status not in {
            RunStatus.CREATED,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
        }:
            raise RunNotDeletableError(
                f"Run {run_id} cannot be deleted while its status is {run.status.value}"
            )

        deleted = await self.runs_repository.delete_run(run_id)
        if not deleted:
            raise ValueError(f"Run {run_id} not found")

    async def launch_run_synch(self, run: Run) -> None:
        await _launch_run(run, self.runs_repository, self, self.redis_client)

    async def get_artifacts_archive(
        self, run_id: str, kind: RunArtifactKind
    ) -> io.BytesIO:
        run = await self.find_by_id(run_id)
        if run.status != RunStatus.COMPLETED:
            raise RunArtifactsUnavailableError(
                f"Run {run_id} artifacts are unavailable while its status is "
                f"{run.status.value}"
            )

        artifacts = self.enumerate_run_artifacts(run, kind)
        missing = [
            artifact.archive_path
            for artifact in artifacts
            if not artifact.source_path.is_file()
        ]
        if missing:
            raise RunArtifactsNotFoundError(missing)

        tar_buffer = io.BytesIO()
        with tarfile.open(
            fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            for artifact in artifacts:
                try:
                    self._add_artifact_to_archive(archive, artifact)
                except FileNotFoundError as error:
                    raise RunArtifactsNotFoundError(
                        [artifact.archive_path]
                    ) from error

        tar_buffer.seek(0)
        return tar_buffer

    def enumerate_run_artifacts(
        self, run: Run, kind: RunArtifactKind
    ) -> list[RunArtifact]:
        """Return the canonical source, archive name, and encoding for a kind."""
        depth = _ARTIFACT_DEPTHS[kind]
        stems = self.assets_repository.get_assets_paths(
            run, depth, self.testbench_settings
        )
        encoding: Literal["file", "numpy-json", "output-analysis-json"] = "file"
        if kind == RunArtifactKind.SAMPLE_MASKS:
            encoding = "numpy-json"
        elif kind == RunArtifactKind.OUTPUT_ANALYSIS:
            encoding = "output-analysis-json"

        artifacts = []
        for stem in stems:
            source_path = Path(
                self.assets_repository.resolve_asset_path(stem, depth)
            )
            artifacts.append(
                RunArtifact(
                    source_path=source_path,
                    archive_path=self._get_artifact_archive_path(source_path, kind),
                    encoding=encoding,
                )
            )
        return artifacts

    def _get_artifact_archive_path(
        self, source_path: Path, kind: RunArtifactKind
    ) -> str:
        try:
            relative_parts = source_path.resolve().relative_to(
                self.assets_repository.get_root_folder()
            ).parts
        except ValueError as error:
            raise RunArtifactConversionError(
                "Run artifact is outside the configured artifact root"
            ) from error

        if kind == RunArtifactKind.ORIGINAL_TRACKS:
            return source_path.name
        if kind == RunArtifactKind.SAMPLE_MASKS:
            return source_path.with_suffix(".json").name
        if kind == RunArtifactKind.RECONSTRUCTED_TRACKS:
            if len(relative_parts) < 3:
                raise RunArtifactConversionError(
                    "Reconstructed-track artifact path has an invalid layout"
                )
            original_track = self._without_suffix(
                relative_parts[-3], "-lost_samples_masks"
            )
            sample_mask = self._without_suffix(
                relative_parts[-2], "-reconstructed_tracks"
            )
            return "/".join([original_track, sample_mask, source_path.name])
        if kind == RunArtifactKind.OUTPUT_ANALYSIS:
            if len(relative_parts) < 4:
                raise RunArtifactConversionError(
                    "Output-analysis artifact path has an invalid layout"
                )
            original_track = self._without_suffix(
                relative_parts[-4], "-lost_samples_masks"
            )
            sample_mask = self._without_suffix(
                relative_parts[-3], "-reconstructed_tracks"
            )
            reconstructed_track = self._without_suffix(
                relative_parts[-2], "-output_analyses"
            )
            return "/".join(
                [
                    original_track,
                    sample_mask,
                    reconstructed_track,
                    source_path.with_suffix(".json").name,
                ]
            )
        raise RunArtifactConversionError(f"Unsupported artifact kind: {kind.value}")

    @staticmethod
    def _without_suffix(value: str, suffix: str) -> str:
        if not value.endswith(suffix):
            raise RunArtifactConversionError(
                f"Run artifact path component does not end with {suffix}"
            )
        return value[: -len(suffix)]

    def _add_artifact_to_archive(
        self, archive: tarfile.TarFile, artifact: RunArtifact
    ) -> None:
        if artifact.encoding == "file":
            archive.add(artifact.source_path, arcname=artifact.archive_path)
            return

        try:
            if artifact.encoding == "numpy-json":
                # pi-lens-ignore: python-insecure-deserialization
                # Sample masks are NumPy files written by our own testbench worker.
                json_value = np.load(
                    artifact.source_path, allow_pickle=True
                ).tolist()
            else:
                with artifact.source_path.open("rb") as artifact_file:
                    # Analyses are pickles written by our own testbench worker.
                    # pi-lens-ignore: python-insecure-deserialization
                    analysis: object = pickle.load(artifact_file)
                if isinstance(analysis, SimpleCalculatorData):
                    json_value = np.nan_to_num(
                        analysis.get_error(), nan=0
                    ).T.tolist()
                elif isinstance(analysis, PEAQData):
                    json_value = [analysis.get_di(), analysis.get_odg()]
                elif isinstance(analysis, np.ndarray):
                    json_value = analysis.tolist()
                else:
                    raise TypeError("Unsupported output-analysis value")

            json_bytes = json.dumps(json_value).encode("utf-8")
        except FileNotFoundError:
            raise
        except (
            OSError,
            EOFError,
            ValueError,
            TypeError,
            AttributeError,
            pickle.PickleError,
        ) as error:
            raise RunArtifactConversionError(
                f"Could not convert run artifact '{artifact.archive_path}' to JSON"
            ) from error

        tar_info = tarfile.TarInfo(name=artifact.archive_path)
        tar_info.size = len(json_bytes)
        archive.addfile(tar_info, io.BytesIO(json_bytes))

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

    async def export_run_config(self, run_id: str) -> str:
        run = await self.find_by_id(run_id)
        config = {
            "name": run.name,
            "tracks": run.tracks,
            "modules": {
                module_type: [
                    {
                        "name": module.name,
                        "settings": [
                            {"name": s.name, "value": s.value} for s in module.settings
                        ],
                    }
                    for module in modules
                ]
                for module_type, modules in run.modules.items()
            },
        }
        return json.dumps(config, indent=2)

    async def validate_run_config(
        self, config: RunConfigDto, modules_service: ModuleService
    ) -> list[RunConfigValidationError]:
        return self._validate_config_modules(config.modules, modules_service)

    async def validate_run_create(
        self, run: RunCreateDto, modules_service: ModuleService
    ) -> list[RunConfigValidationError]:
        return self._validate_config_modules(run.modules, modules_service)

    def _validate_config_modules(
        self,
        modules: dict[ModuleType, list[Module]],
        modules_service: ModuleService,
    ) -> list[RunConfigValidationError]:
        errors: list[RunConfigValidationError] = []
        validator = ModuleConfigValidator(modules_service)

        for module_type, module_list in (modules or {}).items():
            available = modules_service.get_all_modules_by_type(module_type)
            available_names = [m.name for m in available]

            for module in module_list or []:
                # Check if the module name is available
                if module.name not in available_names:
                    errors.append(
                        RunConfigValidationError(
                            module_type=module_type.value,
                            module_name=module.name,
                            error="Modulo non trovato",
                        )
                    )
                    continue
                # Check if the module parameters are valid
                available_module = next(m for m in available if m.name == module.name)
                expected_params = [p.name for p in available_module.settings]
                actual_params = [p.name for p in module.settings]

                # Check if the actual parameters match the expected parameters
                if actual_params != expected_params:
                    errors.append(
                        RunConfigValidationError(
                            module_type=module_type.value,
                            module_name=module.name,
                            error=(
                                f"Parametri non validi. Attesi: {expected_params}, "
                                f"ricevuti: {actual_params}"
                            ),
                        )
                    )
                    continue

                # Check that the provided values respect the manifest validation
                for message in validator.validate_module(module_type, module):
                    errors.append(
                        RunConfigValidationError(
                            module_type=module_type.value,
                            module_name=module.name,
                            setting=message.setting,
                            error=message.message,
                        )
                    )

        return errors
