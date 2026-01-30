"""Shared Generator-Function."""

import math
import sys
import time
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from contextlib import ExitStack
from multiprocessing import Pool
from pathlib import Path
from types import FrameType
from types import TracebackType
from typing import Any

import numpy as np
from shepherd_core.config import config
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.task import Compression
from shepherd_core.exit_handler import activate_exit_handler
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log
from tqdm.auto import trange

from shepherd_core import Writer as ShepherdWriter

# a static seed allows scaling up node count & duration of recordings without altering the dataset
common_seed: int = 32220789340897324098232347119065234157809


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


class EEnvGenerator(ABC):
    """Abstract Base Class for defining custom environment-generators.

    It handles reproducible randomness.
    The main method produces data for a specific time-frame for all nodes.

    TODO: some possible improvements if this gets used more often
        - decouple generation from storage to control what is multi-processed
        - MP storage is only useful on SSD
        - MP calc is only useful if outer loop is not already MP
        - a more finegrained pool queue system would be nice
        - all generators could share a global RAM-Buffer (with backpressure)
        - decoupling should help getting a global progress-bar
    """

    STEP_WIDTH: float = 1.0 / config.SAMPLERATE_SPS  # 10 us

    def __init__(
        self,
        datatype: EnergyDType,
        node_count: int,
        seed: int | list[int] | None,
        window_size: int = 0,
    ) -> None:
        self.datatype = datatype
        self.window_size = window_size
        self.node_count = node_count
        self.rnd_gen = np.random.Generator(bit_generator=np.random.PCG64(seed))
        self.incomplete = None

    def __exit__(
        self,
        typ: type[BaseException] | None = None,
        exc: BaseException | None = None,
        tb: TracebackType | None = None,
        extra_arg: int = 0,
    ) -> None:
        if not isinstance(self.incomplete, list):
            return
        for path in self.incomplete:
            if path.exists():
                log.warning("Will delete incomplete file: %s", path.name)
                path.unlink()

    @abstractmethod
    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        pass

    def generate_h5_files(self, file_paths: list[Path], duration: float, chunk_size: int) -> None:
        """Apply Generator to create valid shepherd files.

        All files are created in parallel with custom chunk-size and duration.
        This function handles the file-format and other parameters.
        The file stem is used as the hostname of the respective file.
        """
        if any(file.exists() for file in file_paths):
            log.info(
                "File(s) exists. Skipping generating h5 files. For %s",
                [file.name for file in file_paths],
            )
            return
        with ExitStack() as stack:
            # Prepare datafiles
            file_handles: list[ShepherdWriter] = []
            self.incomplete = file_paths
            for file_path in file_paths:
                writer = ShepherdWriter(
                    file_path=file_path,
                    compression=Compression.gzip1,
                    mode="harvester",
                    datatype=self.datatype,
                    window_samples=self.window_size,
                    cal_data=CalibrationSeries(
                        # sheep can skip scaling if cal is ideal (applied here)
                        voltage=CalibrationPair(gain=1e-6, offset=0),
                        current=CalibrationPair(gain=1e-9, offset=0),
                    ),
                    verbose=False,
                )
                file_handles.append(stack.enter_context(writer))
                writer.store_hostname(file_path.stem)

            log.debug("Generating energy environment...")
            chunk_duration = chunk_size * self.STEP_WIDTH
            chunk_count = math.ceil(duration / chunk_duration)
            times_per_chunk = np.arange(0, chunk_size) * self.STEP_WIDTH

            start_time = time.time()
            for i in trange(chunk_count, desc="Generating", leave=False):
                times_unfiltered = chunk_duration * i + times_per_chunk
                times = times_unfiltered[np.where(times_unfiltered <= duration)]
                count = len(times)

                iv_pairs = self.generate_iv_pairs(count=count)

                for file, (voltages, currents) in zip(file_handles, iv_pairs, strict=True):
                    file.append_iv_data_si(times, voltages, currents)
            self.incomplete = None
            end_time = time.time()
            log.debug("Done! Generation took %.2f s", end_time - start_time)
