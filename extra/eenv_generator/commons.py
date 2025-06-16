"""Shared Generator-Function."""

import math
import time
from abc import ABC
from abc import abstractmethod
from contextlib import ExitStack
from pathlib import Path
from typing import Optional

import numpy as np
from tqdm import trange

from shepherd_core import Writer as ShepherdWriter
from shepherd_core.config import config
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.task import Compression
from shepherd_core.logger import log

STEP_WIDTH = 1.0 / config.SAMPLERATE_SPS  # 10 us


class EEnvGenerator(ABC):
    """Abstract Base Class for defining custom environment-generators.

    It handled reproducible randomness.
    The main method produces data for a specific time-frame for all nodes.
    """

    def __init__(self, node_count: int, seed: Optional[int]) -> None:
        self.node_count = node_count
        if seed is not None:
            self.rnd_gen = np.random.Generator(bit_generator=np.random.PCG64(seed))

    @abstractmethod
    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        pass


def generate_h5_files(
    output_dir: Path, duration: float, chunk_size: int, generator: EEnvGenerator
) -> None:
    """Apply Generator to create valid shepherd files.

    All files are created in parallel with custom chunk-size and duration.
    This function handles the file-format and other parameters.
    """
    with ExitStack() as stack:
        # Prepare datafiles
        file_handles: list[ShepherdWriter] = []
        for i in range(generator.node_count):
            writer = ShepherdWriter(
                file_path=output_dir / f"node{i}.h5",
                compression=Compression.gzip1,
                mode="harvester",
                datatype=EnergyDType.ivtrace,  # IV-trace
                window_samples=0,  # 0 since dt is IV-trace
                cal_data=CalibrationSeries(
                    # sheep can skip scaling if cal is ideal
                    voltage=CalibrationPair(gain=1e-6, offset=0),
                    current=CalibrationPair(gain=1e-9, offset=0),
                ),
                verbose=False,
            )
            file_handles.append(stack.enter_context(writer))
            writer.store_hostname(f"node{i}.h5")

        log.info("Generating energy environment...")
        chunk_duration = chunk_size * STEP_WIDTH
        chunk_count = math.ceil(duration / chunk_duration)
        times_per_chunk = np.arange(0, chunk_size) * STEP_WIDTH

        start_time = time.time()
        for i in trange(chunk_count, desc="Generating chunk: ", leave=False):
            times_unfiltered = chunk_duration * i + times_per_chunk
            times = times_unfiltered[np.where(times_unfiltered <= duration)]
            count = len(times)

            iv_pairs = generator.generate_iv_pairs(count=count)

            for file, (voltages, currents) in zip(file_handles, iv_pairs):
                file.append_iv_data_si(times, voltages, currents)
        end_time = time.time()
        log.info("Done! Generation took %.2f s", end_time - start_time)
