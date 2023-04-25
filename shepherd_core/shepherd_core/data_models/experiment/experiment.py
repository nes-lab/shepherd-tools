from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List
from typing import Optional

from ..model_shepherd import ShpModel
from ..testbed.target import Target
from .emulator import Emulator


class Experiment(ShpModel):
    # taken from emulation TODO
    output_path: Optional[
        Path
    ]  # TODO: should get default filename (rec_timestamp_observerID.h5)
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF

    #
    emulator_default: Emulator

    #    observer_config: List[Observer]  # TODO
    targets: List[Target]
    # TODO: link list of targets to
    #       - emulator-configs and
    #       - firmware / programmings
