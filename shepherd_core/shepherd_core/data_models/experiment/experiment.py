import hashlib
from datetime import datetime
from datetime import timedelta
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import conlist
from pydantic import constr
from pydantic import root_validator

from ..base.shepherd import ShpModel
from ..testbed.target import Target
from ..testbed.testbed import Testbed
from .observer_features import SystemLogging
from .target_config import TargetConfig


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed
    emulating Energy Environments for Target Nodes"""

    # General Properties
    id: constr(to_lower=True, max_length=16, regex=r"^[\w]*$") = Field(  # noqa: A003
        description="Unique ID (AlphaNum > 4 chars)",
        default=hashlib.sha3_224(str(datetime.now()).encode("utf-8")).hexdigest()[-16:],
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

    @root_validator(pre=False)
    def post_validation(cls, values: dict):
        target_ids = []
        for _config in values["target_configs"]:
            for _id in _config.target_IDs:
                target_ids.append(str(_id).lower())
                Target(id=_id)
                # ⤷ this can raise exception for non-existing targets
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Target-IDs in Experiment got used more than once!")

        testbed = Testbed(name="shepherd_tud_nes")
        target_observers = []
        for _id in target_ids:
            has_hit = False
            for _observer in testbed.observers:
                has_tgt_a = isinstance(_observer.target_a, Target)
                if has_tgt_a and _id == str(_observer.target_a.id).lower():
                    target_observers.append(_observer.id)
                    has_hit = True
                    break
                has_tgt_b = isinstance(_observer.target_b, Target)
                if has_tgt_b and _id == str(_observer.target_b.id).lower():
                    target_observers.append(_observer.id)
                    has_hit = True
                    break
            if not has_hit:
                raise ValueError(f"Target-ID {_id} was not found in Testbed")
        if len(target_ids) != len(set(target_observers)):
            raise ValueError("Observers in Experiment got used more than once!")
        return values
