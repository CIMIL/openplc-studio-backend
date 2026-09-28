from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

DOCUMENTATION_ROUTE = "/plctestbench-docs"
DEFAULT_DOCUMENTATION_DIRECTORY = Path("static/plctestbench-docs")

logger = logging.getLogger(__name__)

_DOCUMENTATION_UNAVAILABLE_PAGE = """<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Documentation unavailable</title></head>
  <body>
    <main>
      <h1>PLCTestbench documentation is unavailable</h1>
      <p>The application is still operational. Rebuild the backend image to generate the documentation site.</p>
    </main>
  </body>
</html>
"""


def resolve_documentation_directory() -> Path:
    configured_path = os.environ.get("PLCTESTBENCH_DOCS_DIRECTORY")
    path = Path(configured_path) if configured_path else DEFAULT_DOCUMENTATION_DIRECTORY
    return path.expanduser().resolve()


def documentation_site_available(directory: Path) -> bool:
    return (directory / "index.html").is_file()


async def documentation_unavailable(request: Request) -> HTMLResponse:
    return HTMLResponse(_DOCUMENTATION_UNAVAILABLE_PAGE, status_code=503)


def mount_documentation(app: FastAPI, directory: str | Path | None = None) -> Path:
    site_directory = (
        Path(directory).expanduser().resolve()
        if directory is not None
        else resolve_documentation_directory()
    )
    available = documentation_site_available(site_directory)
    app.state.plctestbench_docs_directory = site_directory
    app.state.plctestbench_docs_available = available

    if available:
        documentation_app = StaticFiles(directory=str(site_directory), html=True)
        logger.info("Serving PLCTestbench documentation from %s", site_directory)
    else:
        documentation_app = Starlette(
            routes=[
                Route("/", documentation_unavailable),
                Route("/{path:path}", documentation_unavailable),
            ]
        )
        logger.warning(
            "PLCTestbench documentation is unavailable at %s; the API will continue without it. "
            "Rebuild the backend image or set PLCTESTBENCH_DOCS_DIRECTORY.",
            site_directory,
        )

    app.mount(DOCUMENTATION_ROUTE, documentation_app, name="plctestbench-docs")
    return site_directory
