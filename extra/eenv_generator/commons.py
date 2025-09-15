"""Shared Generator-Function."""

import math
import time
from abc import ABC
from abc import abstractmethod
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from shepherd_core.config import config
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.task import Compression
from shepherd_core.logger import log
from tqdm import trange

from shepherd_core import Writer as ShepherdWriter


class EEnvGenerator(ABC):
    """Abstract Base Class for defining custom environment-generators.

    It handles reproducible randomness.
    The main method produces data for a specific time-frame for all nodes.
    """

    STEP_WIDTH: float = 1.0 / config.SAMPLERATE_SPS  # 10 us

    def __init__(
        self,
        datatype: EnergyDType,
        node_count: int,
        seed: None | int | list[int],
        window_size: int = 0,
    ) -> None:
        self.datatype = datatype
        self.window_size = window_size
        self.node_count = node_count
        self.rnd_gen = np.random.Generator(bit_generator=np.random.PCG64(seed))

    @abstractmethod
    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        pass

    def generate_h5_files(self, file_paths: list[Path], duration: float, chunk_size: int) -> None:
        """Apply Generator to create valid shepherd files.

        All files are created in parallel with custom chunk-size and duration.
        This function handles the file-format and other parameters.
        The file stem is used as the hostname of the respective file.
        """
        with ExitStack() as stack:
            # Prepare datafiles
            file_handles: list[ShepherdWriter] = []
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

            log.info("Generating energy environment...")
            chunk_duration = chunk_size * self.STEP_WIDTH
            chunk_count = math.ceil(duration / chunk_duration)
            times_per_chunk = np.arange(0, chunk_size) * self.STEP_WIDTH

            start_time = time.time()
            for i in trange(chunk_count, desc="Generating chunk: ", leave=False):
                times_unfiltered = chunk_duration * i + times_per_chunk
                times = times_unfiltered[np.where(times_unfiltered <= duration)]
                count = len(times)

                iv_pairs = self.generate_iv_pairs(count=count)

                for file, (voltages, currents) in zip(file_handles, iv_pairs, strict=True):
                    file.append_iv_data_si(times, voltages, currents)
            end_time = time.time()
            log.info("Done! Generation took %.2f s", end_time - start_time)
