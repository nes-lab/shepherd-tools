from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Optional

from pydantic import root_validator

from ..base.shepherd import ShpModel
from ..content.virtual_harvester import VirtualHarvesterConfig
from ..experiment.observer_features import PowerTracing
from ..experiment.observer_features import SystemLogging
from .emulation import Compression


class HarvestTask(ShpModel):
    """Configuration for the Observer in Harvest-Mode
    Record IV data from a harvest-source
    """

    # General config
    output_path: Path
    # ⤷ dir- or file-path for storing the recorded data:
    #   - providing a directory -> file is named hrv_timestamp.h5
    #   - for a complete path the filename is not changed except it exists and
    #     overwrite is disabled -> name#num.h5
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

    virtual_harvester: VirtualHarvesterConfig = VirtualHarvesterConfig(name="mppt_opt")
    # ⤷ Choose one of the predefined virtual harvesters
    #   or configure a new one

    power_tracing: Optional[PowerTracing] = PowerTracing()
    sys_logging: Optional[SystemLogging] = SystemLogging()

    # TODO: there is an unused DAC-Output patched to the harvesting-port

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        # TODO: limit paths
        has_start = values.get("time_start") is not None
        if has_start and values["time_start"] < datetime.utcnow():
            raise ValueError("Start-Time for Harvest can't be in the past.")
        return values
