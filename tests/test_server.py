from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from plc_platform_backend.server import _get_int_environment, run_server


class ServerLauncherTests(TestCase):
    def test_runs_uvicorn_with_shared_logging_and_runtime_options(self) -> None:
        configuration = SimpleNamespace(validate_configuration=MagicMock())
        logging_config = {"version": 1}

        with (
            patch(
                "plc_platform_backend.server.get_configuration",
                return_value=configuration,
            ),
            patch(
                "plc_platform_backend.server.build_logging_config",
                return_value=logging_config,
            ),
            patch("plc_platform_backend.server.uvicorn.run") as uvicorn_run,
            patch.dict(
                "os.environ",
                {
                    "API_HOST": "127.0.0.2",
                    "API_PORT": "9000",
                    "API_WORKERS": "3",
                    "FORWARDED_ALLOW_IPS": "10.0.0.1",
                },
                clear=True,
            ),
        ):
            run_server()

        configuration.validate_configuration.assert_called_once_with()
        uvicorn_run.assert_called_once_with(
            "plc_platform_backend.main:app",
            host="127.0.0.2",
            port=9000,
            reload=False,
            workers=3,
            proxy_headers=True,
            forwarded_allow_ips="10.0.0.1",
            log_config=logging_config,
            log_level=None,
        )

    def test_reload_forces_one_worker(self) -> None:
        configuration = SimpleNamespace(validate_configuration=MagicMock())

        with (
            patch(
                "plc_platform_backend.server.get_configuration",
                return_value=configuration,
            ),
            patch("plc_platform_backend.server.uvicorn.run") as uvicorn_run,
            patch.dict("os.environ", {"API_WORKERS": "4"}, clear=True),
        ):
            run_server(reload=True)

        self.assertEqual(uvicorn_run.call_args.kwargs["workers"], 1)
        self.assertTrue(uvicorn_run.call_args.kwargs["reload"])

    def test_rejects_non_integer_environment_values(self) -> None:
        with patch.dict("os.environ", {"API_PORT": "not-a-port"}, clear=True):
            with self.assertRaisesRegex(ValueError, "API_PORT must be an integer"):
                _get_int_environment("API_PORT", 8000)
