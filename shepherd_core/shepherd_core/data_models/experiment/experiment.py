import hashlib
from datetime import datetime
from datetime import timedelta
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import conlist
from pydantic import constr

from ..base.shepherd import ShpModel
from .observer_features import SystemLogging
from .target_config import TargetConfig


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed
    emulating Energy Environments for Target Nodes"""

    # General Properties
    uid: constr(to_lower=True, max_length=16, regex=r"^[\w]*$") = Field(
        description="Unique ID (AlphaNum > 4 chars)",
        default=hashlib.sha3_224(str(datetime.now).encode("utf-8")).hexdigest()[-16:],
    )
    name: constr(max_length=32, regex=r"^[\w\-\s]*$")
    description: Optional[str] = Field(description="Required for public instances")
    comment: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access, TODO

    # feedback
    email_results: Optional[EmailStr]
    sys_logging: SystemLogging = SystemLogging(log_dmesg=True, log_ptp=False)

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    # targets
    target_configs: conlist(item_type=TargetConfig, min_items=1, max_items=64)
