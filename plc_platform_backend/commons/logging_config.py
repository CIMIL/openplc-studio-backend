from __future__ import annotations

import logging
import logging.config
import os
import time
from typing import Any

TRACE_LOG_LEVEL = 5
DEFAULT_LOG_LEVEL = "info"
LOG_FORMAT = (
    "%(asctime)s.%(msecs)03dZ %(levelname)s "
    "[%(process)d:%(threadName)s] %(name)s: %(message)s"
)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_LOG_LEVELS = {
    "trace": TRACE_LOG_LEVEL,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class UtcFormatter(logging.Formatter):
    converter = time.gmtime


def resolve_log_level(value: str | None = None) -> int:
    level_name = (value or os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)).lower()
    try:
        return _LOG_LEVELS[level_name]
    except KeyError as error:
        supported = ", ".join(_LOG_LEVELS)
        raise ValueError(
            f"Invalid LOG_LEVEL '{level_name}'. Expected one of: {supported}."
        ) from error


def build_logging_config(level: str | None = None) -> dict[str, Any]:
    resolved_level = resolve_log_level(level)
    logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")

    shared_logger = {
        "handlers": [],
        "level": resolved_level,
        "propagate": True,
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "plc_platform_backend.commons.logging_config.UtcFormatter",
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": resolved_level,
                "stream": "ext://sys.stderr",
            }
        },
        "root": {
            "handlers": ["console"],
            "level": resolved_level,
        },
        "loggers": {
            "plc_platform_backend": shared_logger.copy(),
            "uvicorn": shared_logger.copy(),
            "uvicorn.error": shared_logger.copy(),
            "uvicorn.access": shared_logger.copy(),
            "dramatiq": shared_logger.copy(),
        },
    }


def configure_logging(level: str | None = None) -> None:
    logging.config.dictConfig(build_logging_config(level))
