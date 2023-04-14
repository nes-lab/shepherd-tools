from datetime import timedelta, datetime
from pathlib import Path
from typing import Optional, List

from pydantic import confloat
from pydantic import conint
from pydantic import constr

from .emulator import Emulator
from ..model_shepherd import ShpModel


class Experiment(ShpModel):

    # from emulation TODO
    output_path: Optional[Path]
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF

    #
    emulator_default: Emulator

    observer_config: List[ObserverConfig]


class ObserverConfig(ShpModel):

    targets: list[Target]
