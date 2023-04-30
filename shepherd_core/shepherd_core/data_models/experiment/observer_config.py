from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import confloat
from pydantic import root_validator

from ..base.shepherd import ShpModel
from ..content.virtual_source import VirtualSource
from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing
from .observer_features import SystemLogging


class TargetPort(str, Enum):
    A = "A"
    B = "B"


class Compression(str, Enum):
    lzf = "lzf"  # not native hdf5
    gzip1 = "1"  # higher compr & load


compressions_allowed: list = [None, "lzf", 1]  # is it still needed?


class ObserverEmulationConfig(ShpModel):
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

    enable_io: bool = False
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

    # TODO: verbosity

    # sub-elements, could be partly moved to emulation
    virtual_source: VirtualSource = VirtualSource(name="neutral")  # {"name": "neutral"}

    # TODO: should these really be here? if no: add gpio_mask
    power_tracing: PowerTracing = PowerTracing()
    gpio_tracing: GpioTracing = GpioTracing()
    gpio_actuation: Optional[GpioActuation]
    sys_logging: SystemLogging = SystemLogging()

    @root_validator(pre=False)
    def post_validation(cls, values: dict):
        # TODO: limit paths
        has_start = values["time_start"] is not None
        if has_start and values["time_start"] < datetime.utcnow():
            raise ValueError("Start-Time for Emulation can't be in the past.")
        return values

    def get_parameters(self):
        # TODO: remove if unneeded
        return self.dict()


# TODO: herdConfig
#  - store if path is remote (read & write)
#   -> so files need to be fetched or have a local path
