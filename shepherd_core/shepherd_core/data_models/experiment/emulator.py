from pathlib import Path
from typing import Optional
from typing import Union

import yaml
from pydantic import confloat
from pydantic import root_validator
from strenum import StrEnum

from .. import ShpModel
from ..model_shepherd import repr_str
from .emulator_features import GpioActuation
from .emulator_features import GpioTracing
from .emulator_features import PowerTracing
from .emulator_features import SystemLogging
from .virtual_source import VirtualSource


class TargetPort(StrEnum):
    A = "A"
    B = "B"


class Compression(StrEnum):
    lzf = "lzf"
    gzip1 = "1"  # TODO: will not work


yaml.add_representer(TargetPort, repr_str)
yaml.add_representer(Compression, repr_str)


compressions_allowed: list = [None, "lzf", 1]


class Emulator(ShpModel):
    # General config
    input_path: Path  # TODO: should be in vsource
    output_path: Optional[Path]
    # ⤷ output_path:
    #   - providing a directory -> file is named emu_timestamp.h5
    #   - for a complete path the filename is not changed except it exists and
    #     overwrite is disabled -> emu#num.h5
    force_overwrite: bool = False
    output_compression: Union[None, str, int] = None
    # ⤷ should be 1 (level 1 gzip), lzf, or None (order of recommendation)

    #    start_time: datetime  # = Field(default_factory=datetime.utcnow)
    #    duration: Optional[timedelta] = None
    # TODO: both could also be "None", interpreted as start ASAP, run till EOF

    # emulation-specific
    use_cal_default: bool = False
    # ⤷ do not load calibration from EEPROM

    enable_io: bool = False
    # ⤷ pre-req for sampling gpio
    io_port: TargetPort = TargetPort.A
    # ⤷ either Port A or B
    # TODO: these two must be optimized - auto-choose depending on target-choice
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
    power_tracing: PowerTracing = PowerTracing()
    gpio_tracing: GpioTracing = GpioTracing()
    gpio_actuation: GpioActuation = GpioActuation()
    sys_logging: SystemLogging = SystemLogging()

    @root_validator()
    def validate(cls, values: dict):
        if isinstance(values, dict):
            comp = values.get("output_compression")
        elif isinstance(values, Emulator):
            comp = values.output_compression
        else:
            raise ValueError("Emulator was not initialized correctly")

        if comp not in compressions_allowed:
            raise ValueError(
                f"value is not allowed ({comp} not in {compressions_allowed}",
            )
        # TODO: limit paths
        # TODO: limit date older than now?
        return values

    @root_validator(pre=False)
    def post_adjust(cls, values: dict):
        # TODO
        return values

    def get_parameters(self):
        # TODO
        return self.dict()
        # pass
