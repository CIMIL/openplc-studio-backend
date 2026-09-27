from unittest import TestCase
from unittest.mock import patch

from plc_platform_backend.worker import main


class WorkerLauncherTests(TestCase):
    def test_runs_dramatiq_with_shared_logging(self) -> None:
        with (
            patch("plc_platform_backend.worker.configure_logging") as configure,
            patch(
                "plc_platform_backend.worker.dramatiq_main", return_value=7
            ) as dramatiq_main,
        ):
            result = main(["--processes", "2"])

        self.assertEqual(result, 7)
        configure.assert_called_once_with()
        parsed_arguments = dramatiq_main.call_args.args[0]
        self.assertEqual(parsed_arguments.broker, "plc_platform_backend.actors")
        self.assertTrue(parsed_arguments.skip_logging)
        self.assertEqual(parsed_arguments.processes, 2)
