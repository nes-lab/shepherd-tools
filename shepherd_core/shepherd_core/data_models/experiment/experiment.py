from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from pydantic import EmailStr
from pydantic import constr

from .. import ShpModel
from .observer_features import SystemLogging
from .target_config import TargetConfig


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed
    emulating Energy Environments for Target Nodes"""

    # general
    name: constr(max_length=32)
    description: Optional[str] = None
    comment: Optional[str] = None

    # feedback
    email_results: Optional[EmailStr]
    sys_logging: SystemLogging = SystemLogging()

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    # targets
    target_configs: List[TargetConfig] = []

    # TODO: exporter for observerCfg
