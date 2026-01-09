"""Generator for random on-off-pattern with fixed periodic window-length and duty cycle."""

import math
from collections.abc import Callable
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
from commons import EEnvGenerator
from commons import process_mp
from commons import root_storage_default
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

        self.period = round(period / self.STEP_WIDTH)
        if not math.isclose(self.period, period / self.STEP_WIDTH):
            raise ValueError("Period * STEP_WIDTH is not an integer")
        self.on_duration = round(duty_cycle * period / self.STEP_WIDTH)

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


def get_worker_configs(
    path_dir: Path = root_storage_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for independent onoff-windows.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    periods: set[float] = {10e-3, 100e-3, 1, 10}
    duty_cycles: set[float] = {0.01, 0.02, 0.05, 0.1, 0.2}
    duration: int = 4 * 60 * 60

    node_count: int = 20
    seed: int = 32220789340897324098232347119065234157809
    chunk_size: int = 10_000_000
    cfgs: list[tuple[Callable, dict[str, Any]]] = []

    for period, duty_cycle in product(periods, duty_cycles):
        # Ensure output folder exists
        folder_path = (
            path_dir
            / "artificial_on_off_windows_random"
            / f"{round(period * 1000.0)}ms_{round(duty_cycle * 100.0)}%"
        )

        if folder_path.exists():
            log.warning("Folder '%s' exists. New node files will be added.", folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)
        # Generate EEnv for this combination
        # Note: Nodes are generated independently to allow adding
        #       nodes without re-generating existing ones

        for node_idx in range(node_count):
            node_path = folder_path / f"node{node_idx:03d}.h5"
            generator = RndPeriodicWindowGenerator(
                node_count=1,
                seed=[seed, node_idx],
                period=period,
                duty_cycle=duty_cycle,
                on_voltage=2.0,
                on_current=10e-3,
            )
            args: dict[str, Any] = {
                "file_paths": [node_path],
                "duration": duration,
                "chunk_size": chunk_size,
            }
            cfgs.append((generator.generate_h5_files, args))
    return cfgs


if __name__ == "__main__":
    process_mp(get_worker_configs())
