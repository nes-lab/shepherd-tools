import copy
from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import confloat
from pydantic import root_validator
from pydantic import validate_arguments

from shepherd_core.data_models.testbed import Testbed

from ..base.content import IdInt
from ..base.shepherd import ShpModel
from ..content.virtual_source import VirtualSourceConfig
from ..experiment.experiment import Experiment
from ..experiment.observer_features import GpioActuation
from ..experiment.observer_features import GpioTracing
from ..experiment.observer_features import PowerTracing
from ..experiment.observer_features import SystemLogging
from ..testbed.cape import TargetPort


class Compression(str, Enum):
    lzf = "lzf"  # not native hdf5
    gzip1 = 1  # higher compr & load
    gzip = 1
    default = 1
    null = None


compressions_allowed: list = [None, "lzf", 1]
c_translate = {"lzf": "lzf", "1": 1, "None": None, None: None}


class EmulationTask(ShpModel):
    """Configuration for the Observer in Emulation-Mode"""

    # General config
    input_path: Path
    # ⤷ hdf5 file containing harvesting data
    output_path: Optional[Path]
    # ⤷ dir- or file-path for storing the recorded data:
    #   - providing a directory -> file is named emu_timestamp.h5
    #   - for a complete path the filename is not changed except it exists and
    #     overwrite is disabled -> emu#num.h5
    # TODO: should the path be mandatory?
    force_overwrite: bool = False
    # ⤷ Overwrite existing file
    output_compression: Optional[Compression] = Compression.default
    # ⤷ should be 1 (level 1 gzip), lzf, or None (order of recommendation)

    time_start: Optional[datetime] = None
    # timestamp or unix epoch time, None = ASAP
    duration: Optional[timedelta] = None
    # ⤷ Duration of recording in seconds, None = till EOF
    abort_on_error: bool = False

    # emulation-specific
    use_cal_default: bool = False
    # ⤷ Use default calibration values, skip loading from EEPROM

    enable_io: bool = False  # TODO: direction of pins!
    # ⤷ Switch the GPIO level converter to targets on/off
    #   pre-req for sampling gpio,
    io_port: TargetPort = TargetPort.A
    # ⤷ Either Port A or B that gets connected to IO
    pwr_port: TargetPort = TargetPort.A
    # ⤷ chosen port will be current-monitored (main, connected to virtual Source),
    #   the other port is aux
    voltage_aux: Union[confloat(ge=0, le=4.5), str] = 0
    # ⤷ aux_voltage options:
    #   - 0-4.5 for specific const Voltage (0 V = disabled),
    #   - "buffer" will output intermediate voltage (storage cap of vsource),
    #   - "main" will mirror main target voltage

    # sub-elements, could be partly moved to emulation
    virtual_source: VirtualSourceConfig = VirtualSourceConfig(
        name="neutral"
    )  # {"name": "neutral"}
    # ⤷ Use the desired setting for the virtual source,
    #   provide parameters or name like BQ25570

    power_tracing: Optional[PowerTracing] = PowerTracing()
    gpio_tracing: Optional[GpioTracing] = GpioTracing()
    gpio_actuation: Optional[GpioActuation] = None
    sys_logging: Optional[SystemLogging] = SystemLogging()

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        # TODO: limit paths
        has_start = values.get("time_start") is not None
        if has_start and values.get("time_start") < datetime.utcnow():
            raise ValueError("Start-Time for Emulation can't be in the past.")
        if isinstance(values.get("voltage_aux"), str) and values.get(
            "voltage_aux"
        ) not in [
            "main",
            "buffer",
        ]:
            raise ValueError(
                "Voltage Aux must be in float (0 - 4.5) or string 'main' / 'mid'."
            )
        if values.get("gpio_actuation") is not None:
            raise ValueError("GPIO Actuation not yet implemented!")
        return values

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment, tb: Testbed, tgt_id: IdInt, root_path: Path):
        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)

        return cls(
            input_path=tb.data_on_observer / tgt_cfg.energy_env.data_path,
            output_path=root_path / f"emu_{obs.name}.h5",
            time_start=copy.copy(xp.time_start),
            duration=xp.duration,
            abort_on_error=xp.abort_on_error,
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
