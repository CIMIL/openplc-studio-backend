from __future__ import annotations

import os

import uvicorn

from plc_platform_backend.commons.configuration import get_configuration
from plc_platform_backend.commons.logging_config import build_logging_config


def _get_int_environment(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got '{value}'.") from error


def run_server(*, reload: bool = False) -> None:
    get_configuration().validate_configuration()

    uvicorn.run(
        "plc_platform_backend.main:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=_get_int_environment("API_PORT", 8000),
        reload=reload,
        workers=1 if reload else _get_int_environment("API_WORKERS", 1),
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "*"),
        log_config=build_logging_config(),
        log_level=None,
    )


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
