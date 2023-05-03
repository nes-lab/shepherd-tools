import copy
from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import confloat
from pydantic import root_validator
from pydantic import validate_arguments

from shepherd_core.data_models.testbed import Testbed

from ..base.shepherd import ShpModel
from ..content.virtual_source import VirtualSource
from ..experiment.experiment import Experiment
from ..experiment.observer_features import GpioActuation
from ..experiment.observer_features import GpioTracing
from ..experiment.observer_features import PowerTracing
from ..experiment.observer_features import SystemLogging
from ..testbed.cape import TargetPort


class Compression(str, Enum):
    lzf = "lzf"  # not native hdf5
    gzip1 = 1  # higher compr & load


compressions_allowed: list = [None, "lzf", 1]  # TODO: is it still needed?


class EmulationTask(ShpModel):
    """Configuration for the Observer in Emulation-Mode"""

    # General config
    input_path: Path
    output_path: Optional[Path]
    # ⤷ output_path:
    #   - providing a directory -> file is named emu_timestamp.h5
    #   - for a complete path the filename is not changed except it exists and
    #     overwrite is disabled -> emu#num.h5
    force_overwrite: bool = False
    output_compression: Optional[Compression] = Compression.lzf
    # ⤷ should be 1 (level 1 gzip), lzf, or None (order of recommendation)

    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF

    # emulation-specific
    use_cal_default: bool = False
    # ⤷ do not load calibration from EEPROM

    enable_io: bool = False  # TODO: direction of pins!
    # ⤷ pre-req for sampling gpio
    io_port: TargetPort = TargetPort.A
    # ⤷ either Port A or B
    pwr_port: TargetPort = TargetPort.A
    # ⤷ that one will be current monitored (main), the other is aux
    voltage_aux: confloat(ge=0, le=5) = 0
    # ⤷ aux_voltage options:
    #   - None to disable (0 V),
    #   - 0-4.5 for specific const Voltage,
    #   - "mid" will output intermediate voltage (vsource storage cap),
    #   - true or "main" to mirror main target voltage

    # sub-elements, could be partly moved to emulation
    virtual_source: VirtualSource = VirtualSource(name="neutral")  # {"name": "neutral"}

    power_tracing: Optional[PowerTracing]
    gpio_tracing: Optional[GpioTracing]
    gpio_actuation: Optional[GpioActuation]
    sys_logging: Optional[SystemLogging]

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        # TODO: limit paths
        has_start = values["time_start"] is not None
        if has_start and values["time_start"] < datetime.utcnow():
            raise ValueError("Start-Time for Emulation can't be in the past.")
        return values

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment, tb: Testbed, tgt_id: int, root_path: Path):
        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)

        return cls(
            input_path=tb.data_on_observer / tgt_cfg.energy_env.data_path,
            output_path=root_path / f"emu_{obs.name}.h5",
            time_start=copy.copy(xp.time_start),
            duration=xp.duration,
            enable_io=(tgt_cfg.gpio_tracing is not None)
            or (tgt_cfg.gpio_actuation is not None),
            io_port=obs.get_target_port(tgt_id),
            pwr_port=obs.get_target_port(tgt_id),
            virtual_source=tgt_cfg.virtual_source,
            power_tracing=tgt_cfg.power_tracing,
            gpio_tracing=tgt_cfg.gpio_tracing,
            gpio_actuation=tgt_cfg.gpio_actuation,
            sys_logging=xp.sys_logging,
        )


# TODO: herdConfig
#  - store if path is remote (read & write)
#   -> so files need to be fetched or have a local path
