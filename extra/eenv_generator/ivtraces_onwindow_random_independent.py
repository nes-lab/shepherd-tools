"""Generator for random on-off-pattern with fixed periodic window-length and duty cycle."""

import math
from itertools import product
from pathlib import Path

import numpy as np
from commons import STEP_WIDTH
from commons import EEnvGenerator
from shepherd_core.data_models import EnergyDType
from shepherd_core.logger import log


class RndPeriodicWindowGenerator(EEnvGenerator):
    """Generates a periodic on-off pattern with fixed on-voltage/-current.

    Each node's has fixed-length on windows placed independently such that the
    duty cycle matches the given value.
    """

    def __init__(
        self,
        node_count: int,
        seed: int | list[int] | None,
        period: float,
        duty_cycle: float,
        on_voltage: float,
        on_current: float,
    ) -> None:
        super().__init__(datatype=EnergyDType.ivtrace, node_count=node_count, seed=seed)

        self.period = round(period / STEP_WIDTH)
        if not math.isclose(self.period, period / STEP_WIDTH):
            raise ValueError("Period * STEP_WIDTH is not an integer")
        self.on_duration = round(duty_cycle * period / STEP_WIDTH)

        # Start at off
        self.states = np.zeros(node_count)
        self.on_voltage = on_voltage
        self.on_current = on_current

    def generate_random_pattern(self, count: int) -> np.ndarray:
        if count % self.period != 0:
            log.warning(
                "Count is not divisible by period step count (%d vs %d)", count, self.period
            )
            count = (round(count / self.period) + 1) * self.period

        period_count = round(count / self.period)
        max_start = self.period - self.on_duration

        samples = np.zeros((count, self.node_count))

        for i in range(period_count):
            period_start = i * self.period
            window_starts = self.rnd_gen.integers(low=0, high=max_start, size=self.node_count)
            for j, start in enumerate(window_starts):
                samples[period_start + start : period_start + start + self.on_duration, j] = 1.0

        return samples

    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        pattern = self.generate_random_pattern(count)
        return [
            (self.on_voltage * pattern[::, i], self.on_current * pattern[::, i])
            for i in range(self.node_count)
        ]


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"

    periods: set[float] = {10e-3, 100e-3, 1, 10}
    duty_cycles: set[float] = {0.01, 0.02, 0.05, 0.1, 0.2}
    duration: int = 4 * 60 * 60

    node_count: int = 20
    seed: int = 32220789340897324098232347119065234157809
    chunk_size: int = 10_000_000

    for period, duty_cycle in product(periods, duty_cycles):
        # Ensure output folder exists
        name = (
            f"artificial_on_off_random_windows_"
            f"{round(period * 1000.0)}ms_{round(duty_cycle * 100.0)}%"
        )
        folder_path = path_eenv / name

        if folder_path.exists():
            log.warning("Folder %s exists. New node files will be added.", folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Generate EEnv for this combination
        # Note: Nodes are generated independently to allow adding
        #       nodes without re-generating existing ones
        log.info(f"Generating EEnv: {name}")
        for node_idx in range(node_count):
            node_path = folder_path / f"node{node_idx:03d}.h5"
            if node_path.exists():
                log.info("File %s exists. Skipping node %i.", node_path, node_idx)
                continue

            generator = RndPeriodicWindowGenerator(
                node_count=1,
                seed=[seed, node_idx],
                period=period,
                duty_cycle=duty_cycle,
                on_voltage=2.0,
                on_current=10e-3,
            )

            try:
                generator.generate_h5_files(
                    file_paths=[node_path], duration=duration, chunk_size=chunk_size
                )
            except:
                # Ensure no unfinished node files remain on exception/interrupt
                # These would be skipped when re-executing, resulting in a broken EEnv
                log.error("Exception encountered. Removing incomplete node file: %s", node_path)
                node_path.unlink()
                raise
