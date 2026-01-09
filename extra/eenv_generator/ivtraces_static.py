"""Generator for static Energy-Environments."""

from collections.abc import Callable
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
from commons import EEnvGenerator
from commons import process_mp
from commons import root_storage_default
from shepherd_core.data_models import EnergyDType


class StaticGenerator(EEnvGenerator):
    """Generator for static Energy-Environments.

    There is only one file needed per use-case since the eenv is
    identical for all nodes.
    Also, no seed is required since no randomness is used.
    """

    def __init__(self, voltage: float, current: float) -> None:
        super().__init__(datatype=EnergyDType.ivsample, node_count=1, seed=None)
        self.voltage = voltage
        self.current = current

    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        voltages = np.repeat(self.voltage, count)
        currents = np.repeat(self.current, count)
        return self.node_count * [(voltages, currents)]


def get_worker_configs(
    path_dir: Path = root_storage_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for static ivtraces.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    voltages: set[float] = {3.0, 2.0}
    currents: set[float] = {50e-3, 10e-3, 5e-3, 1e-3}
    duration: int = 4 * 60 * 60
    folder_path = path_dir / "artificial_static"
    folder_path.mkdir(parents=True, exist_ok=True)
    cfgs: list[tuple[Callable, dict[str, Any]]] = []
    for voltage, current in product(voltages, currents):
        generator = StaticGenerator(voltage=voltage, current=current)
        name = f"{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA.h5"
        args: dict[str, Any] = {
            "file_paths": [folder_path / name],
            "duration": duration,
            "chunk_size": 10_000_000,
        }
        cfgs.append((generator.generate_h5_files, args))
    return cfgs


if __name__ == "__main__":
    process_mp(get_worker_configs())
