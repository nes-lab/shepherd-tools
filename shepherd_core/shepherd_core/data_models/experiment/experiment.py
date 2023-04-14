from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List
from typing import Optional

from shepherd_core.data_models.testbed.observer import Observer
from shepherd_core.data_models.testbed.target import Target

from ..model_shepherd import ShpModel
from .emulator import Emulator


class Experiment(ShpModel):
    # from emulation TODO
    output_path: Optional[Path]
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF

    #
    emulator_default: Emulator

    observer_config: List[Observer]


class ObserverConfig(ShpModel):
    targets: list[Target]
