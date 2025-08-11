"""Generator for on-off-pattern with random on-duration and duty cycle."""

from itertools import product
from pathlib import Path

import numpy as np
from commons import STEP_WIDTH
from commons import EEnvGenerator

from shepherd_core.logger import log


class RndIndepPatternGenerator(EEnvGenerator):
    """Generates a random on-off pattern with fixed on-voltage/-current.

    Each node's state is independently generated such that the average
    duty cycle and on duration match the given values using a markov process.
    """

    def __init__(
        self,
        node_count: int,
        seed: None | int | list[int],
        avg_duty_cycle: float,
        avg_on_duration: float,
        on_voltage: float,
        on_current: float,
    ) -> None:
        super().__init__(node_count, seed)

        avg_on_steps = avg_on_duration / STEP_WIDTH
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


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"

    duty_cycles = [0.01, 0.02, 0.05, 0.1, 0.2]
    on_durations = [100e-6, 500e-6, 1e-3, 5e-3]
    duration = 4 * 60 * 60.0

    node_count = 20
    seed = 32220789340897324098232347119065234157809
    chunk_size = 10_000_000

    for duty_cycle, on_duration in product(duty_cycles, on_durations):
        # Ensure output folder exists
        name = (
            "artificial_on_off_random_markov_avg_"
            f"{round(duty_cycle * 100.0)}%_{round(on_duration * 1e6)}us"
        )
        folder_path = path_eenv / name

        if folder_path.exists():
            log.warning("Folder %s exists. New node files will be added.", folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Generate EEnv for this combination
        # Note: Nodes are generated independently to allow adding
        #       nodes without re-generating existing ones
        log.info("Generating EEnv: %s", name)
        for node_idx in range(node_count):
            node_path = folder_path / f"node{node_idx}.h5"
            if node_path.exists():
                log.info("File %s exists. Skipping node %i.", node_path, node_idx)
                continue

            generator = RndIndepPatternGenerator(
                node_count=1,
                seed=[seed, node_idx],
                avg_duty_cycle=duty_cycle,
                avg_on_duration=on_duration,
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
