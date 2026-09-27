from __future__ import annotations

import sys
from collections.abc import Sequence

from dramatiq.cli import main as dramatiq_main
from dramatiq.cli import make_argument_parser

from plc_platform_backend.commons.logging_config import configure_logging


def main(arguments: Sequence[str] | None = None) -> int:
    configure_logging()

    worker_arguments = [
        "plc_platform_backend.actors",
        "--skip-logging",
        *(arguments or ()),
    ]
    parsed_arguments = make_argument_parser().parse_args(worker_arguments)
    return dramatiq_main(parsed_arguments)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
