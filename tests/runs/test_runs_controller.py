import io
import os
from unittest import TestCase
from unittest.mock import AsyncMock

os.environ.setdefault("MONGO_INITDB_ROOT_USERNAME", "test")
os.environ.setdefault("MONGO_INITDB_ROOT_PASSWORD", "test")
os.environ.setdefault("PLC_ROOT_FOLDER", "/tmp/plc-testbench-tests")
os.environ.setdefault("PLUGINS_DIRECTORY", "/tmp/plc-testbench-tests/plugins")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plc_platform_backend.runs.runs_controller import (
    _ARCHIVE_CHUNK_SIZE,
    _iter_buffer_chunks,
    router,
)
from plc_platform_backend.runs.runs_service import (
    RunArtifactConversionError,
    RunArtifactsNotFoundError,
    RunArtifactsUnavailableError,
    get_runs_service,
)


class RunArtifactsArchiveControllerTests(TestCase):
    def setUp(self) -> None:
        self.service = AsyncMock()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_runs_service] = lambda: self.service
        self.client = TestClient(app)
        self.url = "/runs/run-1/artifacts/original-tracks/archive"

    def test_returns_named_tar_representation(self) -> None:
        self.service.get_artifacts_archive.return_value = io.BytesIO(b"tar-data")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"tar-data")
        self.assertEqual(response.headers["content-type"], "application/x-tar")
        self.assertEqual(response.headers["content-length"], str(len(b"tar-data")))
        self.assertEqual(
            response.headers["content-disposition"],
            "attachment; filename=run_run-1_original-tracks.tar",
        )

    def test_streams_binary_data_in_fixed_size_chunks(self) -> None:
        payload = b"\n" * (_ARCHIVE_CHUNK_SIZE * 2 + 17)
        buffer = io.BytesIO(payload)

        chunks = list(_iter_buffer_chunks(buffer))

        self.assertEqual(
            [len(chunk) for chunk in chunks],
            [_ARCHIVE_CHUNK_SIZE, _ARCHIVE_CHUNK_SIZE, 17],
        )
        self.assertEqual(b"".join(chunks), payload)
        self.assertTrue(buffer.closed)

    def test_rejects_unknown_artifact_kind_with_422(self) -> None:
        response = self.client.get(
            "/runs/run-1/artifacts/unknown-kind/archive"
        )

        self.assertEqual(response.status_code, 422)
        self.service.get_artifacts_archive.assert_not_awaited()

    def test_maps_missing_run_to_404(self) -> None:
        self.service.get_artifacts_archive.side_effect = ValueError("Run not found")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Run not found")

    def test_maps_unavailable_run_to_409(self) -> None:
        self.service.get_artifacts_archive.side_effect = RunArtifactsUnavailableError(
            "Run is not complete"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Run is not complete")

    def test_maps_missing_artifacts_to_404(self) -> None:
        self.service.get_artifacts_archive.side_effect = RunArtifactsNotFoundError(
            ["track.wav"]
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["artifacts"], ["track.wav"])

    def test_maps_conversion_failures_to_422(self) -> None:
        self.service.get_artifacts_archive.side_effect = RunArtifactConversionError(
            "Invalid analysis"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Invalid analysis")
