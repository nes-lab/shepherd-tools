"""Generator for on-off-pattern with random on-duration and duty cycle."""

from itertools import product
from pathlib import Path

import numpy as np
from commons import STEP_WIDTH
from commons import EEnvGenerator
from commons import generate_h5_files

from shepherd_core import logger


class RndIndepPatternGenerator(EEnvGenerator):
    """Generates a random on-off pattern with fixed on-voltage/-current.

    Each node's state is independently generated such that the average
    duty cycle and on duration match the given values using a markov process.
    """

    def __init__(
        self,
        node_count: int,
        seed: int,
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

        for i in range(count):
            # Start from last states
            last_states = samples[i - 1] if i > 0 else self.states
            # Generate random vector (1 value per node)
            random = self.rnd_gen.random(self.node_count)
            # Get probability vector
            probabilities = self.transition_probs[last_states.astype(int)]
            # Generate updated states
            samples[i] = random < probabilities

        # Save last states for next chunk
        self.states = samples[len(samples) - 1]

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

    seed = 32220789340897324098232347119065234157809
    duty_cycles = [0.01, 0.02, 0.05, 0.1, 0.2]
    on_durations = [100e-6, 500e-6, 1e-3, 5e-3]
    duration = 4 * 60 * 60.0

    for duty_cycle, on_duration in product(duty_cycles, on_durations):
        generator = RndIndepPatternGenerator(
            node_count=20,
            seed=seed,
            avg_duty_cycle=duty_cycle,
            avg_on_duration=on_duration,
            on_voltage=2.0,
            on_current=10e-3,
        )

        # Create output folder (or skip)
        name = (
            "artificial_on_off_random_markov_avg_"
            f"{round(duty_cycle * 100.0)}%_{round(on_duration * 1e6)}us"
        )
        folder_path = path_eenv / name
        if folder_path.exists():
            logger.info("Folder %s exists. Skipping combination.", folder_path)
            continue
        folder_path.mkdir(parents=True, exist_ok=False)

        generate_h5_files(folder_path, duration=duration, chunk_size=500_000, generator=generator)
