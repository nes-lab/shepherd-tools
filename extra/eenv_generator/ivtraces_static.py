"""Generator for static Energy-Environments."""

from itertools import product
from pathlib import Path

import numpy as np
from commons import EEnvGenerator
from commons import generate_h5_files

from shepherd_core.logger import log


class StaticGenerator(EEnvGenerator):
    """Generator for static Energy-Environments.

    There is only one file needed per use-case since the eenv is
    identical for all nodes.
    Also, no seed is required since no randomness is used.
    """

    def __init__(self, voltage: float, current: float) -> None:
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

    voltages: set[float] = {3.0, 2.0}
    currents: set[float] = {50e-3, 10e-3, 5e-3, 1e-3}
    duration: int = 10 * 60 * 60

    for voltage, current in product(voltages, currents):
        generator = StaticGenerator(voltage=voltage, current=current)

        # Create output folder (or skip)
        name = f"artificial_static_{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA"
        folder_path = path_eenv / name
        if folder_path.exists():
            log.info("Folder %s exists. Skipping combination.", folder_path)
            continue
        folder_path.mkdir(parents=True, exist_ok=False)

        generate_h5_files(
            folder_path, duration=duration, chunk_size=10_000_000, generator=generator
        )
