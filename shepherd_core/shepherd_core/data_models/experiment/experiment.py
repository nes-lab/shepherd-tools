from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List
from typing import Optional

from pydantic import EmailStr
from pydantic import constr

from .. import ShpModel
from .target_cfg import TargetCfg


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed"""

    # general
    name: constr(max_length=32)
    description: Optional[str] = None
    comment: Optional[str] = None

    # feedback
    output_path: Optional[Path]
    # ⤷ TODO: should get default filename (rec_timestamp_observerID.h5)
    # ⤷ TODO taken from emulation, double
    # ⤷ TODO needs datatype
    email_results: Optional[EmailStr]

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    #
    # emulator_default: Emulator

    #    observer_config: List[Observer]  # TODO
    # targets: List[Target]  # TODO
    target_cfgs: List[TargetCfg] = []  # TODO
    # TODO: link list of targets to
    #       - emulator-configs and
    #       - firmware / programmings
