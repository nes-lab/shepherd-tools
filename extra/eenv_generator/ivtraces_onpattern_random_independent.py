"""Generator for on-off-pattern with random on-duration and duty cycle."""

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


class RndIndepPatternGenerator(EEnvGenerator):
    """Generates a random on-off pattern with fixed on-voltage/-current.

    Each node's state is independently generated such that the average
    duty cycle and on duration match the given values using a markov process.
    """

    def __init__(
        self,
        node_count: int,
        seed: int | list[int] | None,
        avg_duty_cycle: float,
        avg_on_duration: float,
        on_voltage: float,
        on_current: float,
    ) -> None:
        super().__init__(datatype=EnergyDType.ivtrace, node_count=node_count, seed=seed)

        avg_on_steps = avg_on_duration / self.STEP_WIDTH
        p2 = 1.0 - (1.0 / avg_on_steps)
        p1 = avg_duty_cycle * (1 - p2) / (1 - avg_duty_cycle)
        self.transition_probs = np.array([p1, p2])

        # Start at off
        self.states = np.zeros(node_count)
        self.on_voltage = on_voltage
        self.on_current = on_current

    def generate_random_pattern(self, count: int) -> np.ndarray:
        samples = np.zeros((count, self.node_count))
        # Pre-Generate random matrix (steps x nodes)
        random = self.rnd_gen.random((count, self.node_count))

        # Start from last states (from last chunk)
        last_states = self.states

        for i in range(count):
            # Get probability vector
            probabilities = self.transition_probs[last_states.astype(int)]
            # Generate updated states
            samples[i] = random[i] < probabilities
            # Save state for next transition
            last_states = samples[i]

        # Save last states for next chunk
        self.states = last_states

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
    """Generate worker-configurations for independent onoff-pattern.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    duty_cycles: set[float] = {0.01, 0.02, 0.05, 0.1, 0.2}
    on_durations: set[float] = {100e-6, 500e-6, 1e-3, 5e-3}
    duration: int = 4 * 60 * 60

    node_count: int = 20
    seed: int = 32220789340897324098232347119065234157809
    chunk_size: int = 10_000_000
    cfgs: list[tuple[Callable, dict[str, Any]]] = []

    for duty_cycle, on_duration in product(duty_cycles, on_durations):
        # Ensure output folder exists
        folder_path = (
            path_dir
            / "artificial_on_off_pattern_markov"
            / f"avg_{round(duty_cycle * 100.0)}%_{round(on_duration * 1e6)}us"
        )

        if folder_path.exists():
            log.warning("Folder '%s' exists. New node files will be added.", folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Generate EEnv for this combination
        # Note: Nodes are generated independently to allow adding
        #       nodes without re-generating existing ones
        for node_idx in range(node_count):
            node_path = folder_path / f"node{node_idx:03d}.h5"
            generator = RndIndepPatternGenerator(
                node_count=1,
                seed=[seed, node_idx],
                avg_duty_cycle=duty_cycle,
                avg_on_duration=on_duration,
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
