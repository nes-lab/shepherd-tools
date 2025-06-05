from pathlib import Path

import numpy as np

from . import STEP_WIDTH
from . import EEnvGenerator
from . import generate_h5_files


class RndIndepPatternGenerator(EEnvGenerator):
    """
    Generates a random on-off pattern with fixed on-voltage/-current.
    Each node's state is independently generated such that the average
    duty cycle and on duration match the given values using a markov process.
    """

    def __init__(self, node_count, seed, avg_duty_cycle, avg_on_duration, on_voltage, on_current):
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
            last = samples[i - 1] if i > 0 else self.states
            # Generate random vector (1 value per node)
            random = self.rnd_gen.random(self.node_count)
            # Get probability vector
            probabilities = self.transition_probs[samples[i - 1].astype(int)]
            # Generate updated states
            samples[i] = random < probabilities

        # Save last states for next chunk
        self.states = samples[len(samples) - 1]

        return samples

    def generate_iv_pairs(self, count) -> list[tuple[np.ndarray, np.ndarray]]:
        pattern = self.generate_random_pattern(count)
        result = [
            (self.on_voltage * pattern[::, i], self.on_current * pattern[::, i])
            for i in range(self.node_count)
        ]
        return result


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"

    seed = 32220789340897324098232347119065234157809
    duration = 1 * 60 * 60.0

    generator = RndIndepPatternGenerator(
        node_count=10,
        seed=seed,
        avg_duty_cycle=0.5,
        avg_on_duration=10e-3,
        on_voltage=1,
        on_current=100e-3,
    )

    # Create folder
    name = "random_pattern_test"
    folder_path = path_eenv / name
    folder_path.mkdir(parents=True, exist_ok=False)

    generate_h5_files(folder_path, duration=duration, chunk_size=500_000, generator=generator)
