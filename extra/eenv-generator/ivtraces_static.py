from itertools import product
from pathlib import Path

import numpy as np

from . import EEnvGenerator
from . import generate_h5_files


class StaticGenerator(EEnvGenerator):
    def __init__(self, voltage: float, current: float) -> None:
        # No seed required since no randomness is used
        # 1 Node is sufficient since
        super().__init__(node_count=1, seed=None)
        self.voltage = voltage
        self.current = current

    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        voltages = np.repeat(self.voltage, count)
        currents = np.repeat(self.current, count)
        return self.node_count * [(voltages, currents)]


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"

    voltages = [3.0, 2.0]
    currents = [50e-3, 10e-3, 5e-3, 1e-3]
    duration = 10 * 60 * 60.0

    for voltage, current in product(voltages, currents):
        generator = StaticGenerator(voltage=voltage, current=current)

        # Create folder
        name = f"eenv_static_{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA"
        folder_path = path_eenv / name
        folder_path.mkdir(parents=True, exist_ok=False)

        generate_h5_files(
            folder_path, duration=duration, chunk_size=10_000_000, generator=generator
        )
