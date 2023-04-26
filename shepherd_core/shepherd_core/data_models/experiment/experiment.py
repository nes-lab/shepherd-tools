from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List
from typing import Optional

from pydantic import EmailStr

from .. import ShpModel
from ..testbed import Target
from .emulator import Emulator


class Experiment(ShpModel):
    # general
    name: str
    description: Optional[str] = None
    comment: Optional[str] = None

    # feedback
    output_path: Optional[Path]
    # ⤷ TODO: should get default filename (rec_timestamp_observerID.h5)
    # ⤷ TODO taken from emulation, double
    email_results: Optional[EmailStr]

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    #
    emulator_default: Emulator

    #    observer_config: List[Observer]  # TODO
    targets: List[Target]
    # TODO: link list of targets to
    #       - emulator-configs and
    #       - firmware / programmings
