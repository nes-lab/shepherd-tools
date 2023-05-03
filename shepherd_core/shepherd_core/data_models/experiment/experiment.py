from datetime import datetime
from datetime import timedelta
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import conlist
from pydantic import root_validator

from ..base.content import id_default
from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.shepherd import ShpModel
from ..testbed.target import Target
from ..testbed.testbed import Testbed
from .observer_features import SystemLogging
from .target_config import TargetConfig


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed
    emulating Energy Environments for Target Nodes"""

    # General Properties
    id: id_int = Field(  # noqa: A003
        description="Unique ID",
        default_factory=id_default,
    )
    name: name_str
    description: Optional[safe_str] = Field(description="Required for public instances")
    comment: Optional[safe_str] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access, TODO
    owner_id: Optional[id_int] = 5472  # UUID?

    # feedback
    email_results: Optional[EmailStr]  # TODO: can be bool, as its linked to account
    sys_logging: SystemLogging = SystemLogging(dmesg=True, ptp=False, shepherd=True)

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    # targets
    target_configs: conlist(item_type=TargetConfig, min_items=1, max_items=64)

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        cls.validate_targets(values)
        cls.validate_observers(values)
        return values

    @staticmethod
    def validate_targets(values: dict):
        target_ids = []
        custom_ids = []
        for _config in values["target_configs"]:
            for _id in _config.target_IDs:
                target_ids.append(_id)
                Target(id=_id)
                # ⤷ this can raise exception for non-existing targets
            if _config.custom_IDs is not None:
                custom_ids = custom_ids + _config.custom_IDs[: len(_config.target_IDs)]
            else:
                custom_ids = custom_ids + _config.target_IDs
        if len(target_ids) > len(set(target_ids)):
            raise ValueError("Target-ID used more than once in Experiment!")
        if len(target_ids) > len(set(custom_ids)):
            raise ValueError(
                "Custom Target-ID are faulty (some form of id-collisions)!"
            )

    @staticmethod
    def validate_observers(values: dict):
        target_ids = []
        for _config in values["target_configs"]:
            for _id in _config.target_IDs:
                target_ids.append(_id)

        testbed = Testbed(name="shepherd_tud_nes")
        obs_ids = []
        for _id in target_ids:
            obs_ids.append(testbed.get_observer(_id).id)
        if len(target_ids) > len(set(obs_ids)):
            raise ValueError(
                "Observer used more than once in Experiment "
                "-> only 1 target per observer!"
            )

    def get_target_ids(self) -> list:
        target_ids = []
        for _config in self.target_configs:
            for _id in _config.target_IDs:
                target_ids.append(_id)
        return target_ids

    def get_target_config(self, target_id: int) -> TargetConfig:
        for _config in self.target_configs:
            if target_id in _config.target_IDs:
                return _config
        raise ValueError(
            f"Target-ID {target_id} was not found in Experiment '{self.name}'"
        )
