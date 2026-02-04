"""Shared Functionality."""

import sys
import time
from collections.abc import Callable
from multiprocessing import Pool
from pathlib import Path
from types import FrameType
from typing import Any

from shepherd_core.exit_handler import activate_exit_handler
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log


def get_path_default() -> Path:
    """Provide the storage directory."""
    if Path("/var/shepherd/").exists():
        return Path("/var/shepherd/content/eenv/nes_lab/")

    path_here = Path(__file__).parent.absolute()
    return path_here / "content/eenv/nes_lab/"


root_storage_default = get_path_default()


def worker(cfg: tuple[Callable, dict[str, Any]]) -> Any:
    """Process configuration by running this workers.

    The tuple should contain a callable function and a dict with its arguments.
    """
    fn, args = cfg
    try:
        fn(**args)
    except (SystemExit, KeyboardInterrupt):
        for path in args.get("file_paths", []):
            if path.exists():
                log.warning("Deleting incomplete file: %s", path.name)
                path.unlink()


def process_mp(worker_cfgs: list[tuple[Callable, dict[str, Any]]]) -> None:
    """Multiprocess each worker."""
    start_time = time.time()
    with Pool() as pool:
        log.info(f"Multiprocessing {len(worker_cfgs)} jobs with {pool._processes} workers")  # noqa: SLF001

        def exit_pool(_signum: int, _frame: FrameType | None) -> None:
            """Provide custom exit handler that closes the pool."""
            pool.terminate()
            log.warning("Exiting!")
            sys.exit(0)

        # TODO: at least windows is not exiting correctly
        activate_exit_handler(exit_pool)
        pool.map(worker, worker_cfgs)

    end_time = time.time()
    log.info("Done! Generation took %.2f s", end_time - start_time)


def process_sp(worker_cfgs: list[tuple[Callable, dict[str, Any]]]) -> None:
    """Single process each worker."""
    increase_verbose_level(3)
    activate_exit_handler()
    log.info(f"Single processing {len(worker_cfgs)} jobs with debug-logging")
    for cfg in worker_cfgs:
        worker(cfg)
