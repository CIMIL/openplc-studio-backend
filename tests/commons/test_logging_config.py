import logging
import re
from unittest import TestCase
from unittest.mock import patch

from plc_platform_backend.commons.logging_config import (
    DATE_FORMAT,
    LOG_FORMAT,
    TRACE_LOG_LEVEL,
    UtcFormatter,
    build_logging_config,
    resolve_log_level,
)


class LoggingConfigurationTests(TestCase):
    def test_uses_info_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            config = build_logging_config()

        self.assertEqual(config["root"]["level"], logging.INFO)
        self.assertEqual(config["handlers"]["console"]["level"], logging.INFO)

    def test_uses_environment_log_level(self) -> None:
        with patch.dict("os.environ", {"LOG_LEVEL": "debug"}, clear=True):
            config = build_logging_config()

        self.assertEqual(config["root"]["level"], logging.DEBUG)
        self.assertEqual(
            config["loggers"]["plc_platform_backend"]["level"], logging.DEBUG
        )

    def test_supports_trace(self) -> None:
        self.assertEqual(resolve_log_level("trace"), TRACE_LOG_LEVEL)
        build_logging_config("trace")
        self.assertEqual(logging.getLevelName(TRACE_LOG_LEVEL), "TRACE")

    def test_rejects_invalid_log_level(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid LOG_LEVEL 'verbose'"):
            resolve_log_level("verbose")

    def test_framework_loggers_share_the_root_handler(self) -> None:
        config = build_logging_config("warning")

        self.assertEqual(config["root"]["handlers"], ["console"])
        for logger_name in (
            "plc_platform_backend",
            "uvicorn",
            "uvicorn.error",
            "uvicorn.access",
            "dramatiq",
        ):
            logger_config = config["loggers"][logger_name]
            self.assertEqual(logger_config["handlers"], [])
            self.assertTrue(logger_config["propagate"])
            self.assertEqual(logger_config["level"], logging.WARNING)

    def test_formatter_uses_readable_utc_shape(self) -> None:
        formatter = UtcFormatter(LOG_FORMAT, DATE_FORMAT)
        record = logging.LogRecord(
            name="plc_platform_backend.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="ready",
            args=(),
            exc_info=None,
        )
        record.created = 0
        record.msecs = 0

        rendered = formatter.format(record)

        self.assertRegex(
            rendered,
            re.compile(
                r"^1970-01-01T00:00:00\.000Z INFO "
                r"\[\d+:MainThread\] plc_platform_backend\.test: ready$"
            ),
        )
