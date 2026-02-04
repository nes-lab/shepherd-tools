"""Generator for static Energy-Environments."""

from collections.abc import Callable
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from commons import EEnvGenerator
from commons import process_mp
from commons import root_storage_default
from pydantic import BaseModel
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models.content import EnergyProfile


class Params(BaseModel):
    """Config model with default parameters."""

    root_path: Path = root_storage_default
    dir_name: str = "synthetic_static"
    duration: int = 1 * 60 * 60
    chunk_size: int = 10_000_000
    # custom config below
    voltages: set[float] = {3.0, 2.0, 1.0}
    currents: set[float] = {50e-3, 20e-3, 10e-3, 5e-3, 2e-3, 1e-3}


params_default = Params()
path_file: Path = Path(__file__)


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
    params: Params = params_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for static ivtraces.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    folder_path = params.root_path / params.dir_name
    folder_path.mkdir(parents=True, exist_ok=True)
    cfgs: list[tuple[Callable, dict[str, Any]]] = []
    for voltage, current in product(params.voltages, params.currents):
        generator = StaticGenerator(voltage=voltage, current=current)
        file_name = f"{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA.h5"
        args: dict[str, Any] = {
            "file_paths": [folder_path / file_name],
            "duration": params.duration,
            "chunk_size": params.chunk_size,
        }
        cfgs.append((generator.generate_h5_files, args))
    return cfgs


def create_meta_data(params: Params = params_default) -> None:
    """Generate a YAML containing the metadata for the dataset.

    Combines data from hdf5-files itself and manually added descriptive data.
    """
    folder_path = params.root_path / params.dir_name
    wraps = []
    for voltage, current in product(params.voltages, params.currents):
        name_ds = f"{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA"
        file_path = folder_path / f"{name_ds}.h5"
        epro = EnergyProfile.derive_from_file(file_path, repetition_ok=True)
        data_update = {
            # pretend data is available on server already (will be copied)
            "data_path": Path("/var/shepherd/content/eenv/nes_lab/")
            / file_path.relative_to(params.root_path),
            "data_2_copy": False,
        }
        epro = epro.model_copy(deep=True, update=data_update)

        eenv = EnergyEnvironment(
            name=f"{params.dir_name}_{name_ds}",
            description=f"Virtual Bench Power Supply, {voltage:.3f} V, {current:.3f} A",
            comment=f"created with {path_file.relative_to(path_file.parents[2])}",
            energy_profiles=[epro],
            owner="Ingmar",
            group="NES_Lab",
            visible2group=True,
            visible2all=True,
            metadata={
                "voltage_V": voltage,
                "current_A": current,
            },
        )
        eenv_wrap = Wrapper(
            datatype=EnergyEnvironment.__name__,
            parameters=eenv.model_dump(exclude_none=True),
        )
        wraps.append(eenv_wrap.model_dump(exclude_unset=True, exclude_defaults=True))

    wraps_yaml = yaml.safe_dump(wraps, default_flow_style=False, sort_keys=False)
    with (folder_path / f"_metadata_eenvs_{params.dir_name}.yaml").open("w") as f:
        f.write(wraps_yaml)


if __name__ == "__main__":
    process_mp(get_worker_configs())
    create_meta_data()
