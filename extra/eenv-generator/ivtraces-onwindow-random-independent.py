import math
from pathlib import Path

import numpy as np
from common import STEP_WIDTH
from common import EEnvGenerator
from common import generate_h5_files


class RndPeriodicWindowGenerator(EEnvGenerator):
    """
    Generates a random on-off pattern with fixed on-voltage/-current.
    Each node's state is independently generated such that the average
    duty cycle and on duration match the given values using a markov process.
    """

    def __init__(self, node_count, seed, period, duty_cycle, on_voltage, on_current) -> None:
        self.period = round(period / STEP_WIDTH)
        assert math.isclose(self.period, period / STEP_WIDTH), (
            "Period * STEP_WIDTH is not an integer"
        )

        self.on_duration = round(duty_cycle * period / STEP_WIDTH)

        super().__init__(node_count, seed)

        # Start at off
        self.states = np.zeros(node_count)
        self.on_voltage = on_voltage
        self.on_current = on_current

    def generate_random_pattern(self, count: int) -> np.ndarray:
        assert count % self.period == 0, "Count is not divisible by period step count"

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

    generator = RndPeriodicWindowGenerator(
        node_count=10, seed=seed, period=10e-3, duty_cycle=0.2, on_voltage=1, on_current=100e-3
    )

    # Create folder
    name = "random_window_test"
    folder_path = path_eenv / name
    folder_path.mkdir(parents=True, exist_ok=False)

    generate_h5_files(folder_path, duration=duration, chunk_size=500_000, generator=generator)
