from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plc_platform_backend.documentation import mount_documentation


def create_site(directory: Path) -> Path:
    directory.mkdir()
    (directory / "index.html").write_text("documentation home", encoding="utf-8")
    guide_directory = directory / "guide"
    guide_directory.mkdir()
    (guide_directory / "index.html").write_text("guide page", encoding="utf-8")
    (directory / "site.css").write_text("body {}", encoding="utf-8")
    return directory


def create_app(site_directory: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_documentation(app, site_directory)
    return app


class DocumentationTests(TestCase):
    def test_serves_documentation_pages_and_assets(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            site = create_site(Path(temporary_directory) / "site")
            app = create_app(site)

            with TestClient(app) as client:
                self.assertEqual(
                    client.get("/plctestbench-docs/").text,
                    "documentation home",
                )
                self.assertEqual(
                    client.get("/plctestbench-docs/guide/").text,
                    "guide page",
                )
                self.assertEqual(
                    client.get("/plctestbench-docs/site.css").text,
                    "body {}",
                )
                self.assertEqual(
                    client.get("/plctestbench-docs/missing.html").status_code,
                    404,
                )
                self.assertTrue(app.state.plctestbench_docs_available)

    def test_missing_documentation_only_disables_docs(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = create_app(Path(temporary_directory) / "missing")

            with TestClient(app) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                response = client.get("/plctestbench-docs/")
                self.assertEqual(response.status_code, 503)
                self.assertIn("application is still operational", response.text)
                self.assertFalse(app.state.plctestbench_docs_available)

    def test_fastapi_swagger_and_package_docs_use_distinct_routes(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            site = create_site(Path(temporary_directory) / "site")
            app = create_app(site)

            with TestClient(app) as client:
                self.assertEqual(client.get("/docs").status_code, 200)
                self.assertEqual(
                    client.get("/plctestbench-docs/").status_code,
                    200,
                )
