"""Generator for random on-off-pattern with fixed periodic window-length and duty cycle."""

import math
from collections.abc import Callable
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from commons import EEnvGenerator
from commons import common_seed
from commons import process_mp
from commons import root_storage_default
from pydantic import BaseModel
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models.content import EnergyProfile
from shepherd_core.logger import log


class Params(BaseModel):
    """Config model with default parameters."""

    root_path: Path = root_storage_default
    dir_name: str = "artificial_on_off_windows_random"
    duration: int = 1 * 60 * 60
    chunk_size: int = 10_000_000
    # custom config below
    voltages: set[float] = {2.0}
    currents: set[float] = {10e-3}
    periods: set[float] = {10e-3, 100e-3, 1, 10}
    duty_cycles: set[float] = {0.01, 0.02, 0.05, 0.1, 0.2}
    node_count: int = 20
    # 20 combinations, 20 nodes, 1h => 20*20*1 = ~400 GB
    metadata: dict[str, Any] = {
        "seed": common_seed,
    }


params_default = Params()


class RndPeriodicWindowGenerator(EEnvGenerator):
    """Generates a periodic on-off pattern with fixed on-voltage/-current.

    Each node has fixed-length on windows placed independently such that the
    duty cycle matches the given value.
    """

    def __init__(
        self,
        node_count: int,
        seed: int | list[int] | None,
        period: float,
        duty_cycle: float,
        on_voltage: float,
        on_current: float,
    ) -> None:
        super().__init__(datatype=EnergyDType.ivtrace, node_count=node_count, seed=seed)

        self.period = round(period / self.STEP_WIDTH)
        if not math.isclose(self.period, period / self.STEP_WIDTH):
            raise ValueError("Period * STEP_WIDTH is not an integer")
        self.on_duration = round(duty_cycle * period / self.STEP_WIDTH)

        # Start at off
        self.states = np.zeros(node_count)
        self.on_voltage = on_voltage
        self.on_current = on_current

    def generate_random_pattern(self, count: int) -> np.ndarray:
        if count % self.period != 0:
            log.warning(
                "Count is not divisible by period step count (%d vs %d)", count, self.period
            )
            count = (round(count / self.period) + 1) * self.period

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


def get_worker_configs(
    params: Params = params_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for independent onoff-windows.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = []

    combinations = product(params.voltages, params.currents, params.periods, params.duty_cycles)
    for voltage, current, period, duty_cycle in combinations:
        name = (
            f"{round(period * 1000.0)}ms_{round(duty_cycle * 100.0)}%_"
            f"{round(voltage * 1000.0)}mV_{round(current * 1000.0)}mA"
        )
        folder_path = params.root_path / params.dir_name / name
        if folder_path.exists():
            log.warning("Folder '%s' exists. New node files will be added.", folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)
        # Note: Nodes are generated independently to allow adding
        #       nodes without re-generating existing ones
        for node_idx in range(params.node_count):
            file_path = folder_path / f"node{node_idx:03d}.h5"
            generator = RndPeriodicWindowGenerator(
                node_count=1,
                seed=[common_seed, node_idx],
                period=period,
                duty_cycle=duty_cycle,
                on_voltage=voltage,
                on_current=current,
            )
            args: dict[str, Any] = {
                "file_paths": [file_path],
                "duration": params.duration,
                "chunk_size": params.chunk_size,
            }
            cfgs.append((generator.generate_h5_files, args))
    return cfgs


def create_meta_data(params: Params = params_default) -> None:
    """Generate a YAML containing the metadata for the dataset.

    Combines data from hdf5-files itself and manually added descriptive data.
    """
    wraps = []

    folder_path = params.root_path / params.dir_name
    combinations = product(params.voltages, params.currents, params.periods, params.duty_cycles)
    for voltage, current, period, duty_cycle in combinations:
        name_ds = (
            f"{round(period * 1000.0)}ms_{round(duty_cycle * 100.0)}%_"
            f"{round(voltage, 1)}V_{round(current * 1000.0)}mA"
        )

        eprofiles: list[EnergyProfile] = []
        for node_idx in range(params.node_count):
            file_path = folder_path / name_ds / f"node{node_idx:03d}.h5"
            epro = EnergyProfile.derive_from_file(file_path)
            data_update = {
                # pretend data is available on server already (will be copied)
                "data_path": Path("/var/shepherd/content/eenv/nes_lab/")
                / file_path.relative_to(params.root_path),
                "data_2_copy": False,
            }
            eprofiles.append(epro.model_copy(deep=True, update=data_update))

        params.metadata["on_voltage_V"] = voltage
        params.metadata["on_current_A"] = current
        params.metadata["duty_cycle"] = duty_cycle
        params.metadata["period_s"] = period

        eenv = EnergyEnvironment(
            name=f"{params.dir_name}_{name_ds}",
            description=(
                "Periodic on-off pattern with fixed on-voltage/-current "
                f"({voltage:.3f} V, {current:.3f} A). "
                "Each node has fixed-length on-windows placed independently "
                "such that the duty cycle matches the given value "
                f"({duty_cycle * 100:.3f} % duty in {period * 1000:.3f} ms period)."
            ),
            comment=f"created with {Path(__file__).name}",
            energy_profiles=eprofiles,
            owner="Ingmar",
            group="NES_Lab",
            visible2group=True,
            visible2all=True,
            metadata=params.metadata,
        )
        eenv_wrap = Wrapper(
            datatype=EnergyEnvironment.__name__,
            parameters=eenv.model_dump(exclude_none=True),
        )
        wraps.append(eenv_wrap.model_dump(exclude_unset=True, exclude_defaults=True))

    wraps_yaml = yaml.safe_dump(wraps, default_flow_style=False, sort_keys=False)
    with (folder_path / "metadata.yaml").open("w") as f:
        f.write(wraps_yaml)


if __name__ == "__main__":
    process_mp(get_worker_configs())
    create_meta_data()
