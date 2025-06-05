import math
from itertools import product
from pathlib import Path

import numpy as np
from commons import STEP_WIDTH
from commons import EEnvGenerator
from commons import generate_h5_files


class RndPeriodicWindowGenerator(EEnvGenerator):
    '''
    Generates a periodic on-off pattern with fixed on-voltage/-current.
    Each node's has fixed-length on windows placed independently such that the
    duty cycle matches the given value.
    '''

    def __init__(
        self,
        node_count: int,
        seed: int,
        period: float,
        duty_cycle: float,
        on_voltage: float,
        on_current: float,
    ) -> None:
        self.period = round(period / STEP_WIDTH)
        if not math.isclose(self.period, period / STEP_WIDTH):
            raise ValueError("Period * STEP_WIDTH is not an integer")

        self.on_duration = round(duty_cycle * period / STEP_WIDTH)

        super().__init__(node_count, seed)

        # Start at off
        self.states = np.zeros(node_count)
        self.on_voltage = on_voltage
        self.on_current = on_current

    def generate_random_pattern(self, count: int) -> np.ndarray:
        if count % self.period != 0:
            raise ValueError("Count is not divisible by period step count")

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

    seed = 32220789340897324098232347119065234157809
    periods = [ 10e-3, 100e-3, 1, 10 ]
    duty_cycles = [ 0.01, 0.02, 0.05, 0.1, 0.2]
    duration = 4 * 60 * 60.0

    for period, duty_cycle in product(periods, duty_cycles):
        generator = RndPeriodicWindowGenerator(
            node_count=20, seed=seed, period=period, duty_cycle=duty_cycle, on_voltage=2, on_current=10e-3
        )

        # Create output folder (or skip)
        name = f"eenv_random_onwidows_{round(period * 1000.0)}ms_{round(duty_cycle * 100.0)}%"
        folder_path = path_eenv / name
        if folder_path.exists():
            print(f'Folder {folder_path} exists. Skipping combination.')
            continue
        folder_path.mkdir(parents=True, exist_ok=False)

        generate_h5_files(folder_path, duration=duration, chunk_size=500_000, generator=generator)
