from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import model_validator
from typing_extensions import Annotated
from typing_extensions import Self

from ..base.content import IdInt
from ..base.content import NameStr
from ..base.content import SafeStr
from ..base.content import id_default
from ..base.shepherd import ShpModel
from ..testbed.target import Target
from ..testbed.testbed import Testbed
from .observer_features import SystemLogging
from .target_config import TargetConfig


class Experiment(ShpModel, title="Config of an Experiment"):
    """Configuration for Experiments on the Shepherd-Testbed
    emulating Energy Environments for Target Nodes
    """

    # General Properties
    id: IdInt = Field(  # noqa: A003
        description="Unique ID",
        default_factory=id_default,
    )
    # ⤷ TODO: automatic ID is problematic for identification by hash
    name: NameStr
    description: Annotated[
        Optional[SafeStr], Field(description="Required for public instances")
    ] = None
    comment: Optional[SafeStr] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access, TODO
    owner_id: Optional[IdInt] = 5472  # UUID?

    # feedback
    email_results: Optional[EmailStr] = None
    # ⤷ TODO: can be bool, as its linked to account
    sys_logging: SystemLogging = SystemLogging(dmesg=True, ptp=True, shepherd=True)

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF
    abort_on_error: bool = False

    # targets
    target_configs: Annotated[List[TargetConfig], Field(min_length=1, max_length=128)]

    # TODO: we probably need to remember the lib-version for content &| experiment

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        self.validate_targets(self.target_configs)
        self.validate_observers(self.target_configs)
        if self.duration and self.duration.total_seconds() < 0:
            raise ValueError("Duration of experiment can't be negative.")
        return self

    @staticmethod
    def validate_targets(configs: List[TargetConfig]) -> None:
        target_ids = []
        custom_ids = []
        for _config in configs:
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
            raise ValueError("Custom Target-ID are faulty (some form of id-collisions)!")

    @staticmethod
    def validate_observers(configs: List[TargetConfig]) -> None:
        target_ids = [_id for _config in configs for _id in _config.target_IDs]

        testbed = Testbed(name="shepherd_tud_nes")
        obs_ids = [testbed.get_observer(_id).id for _id in target_ids]
        if len(target_ids) > len(set(obs_ids)):
            raise ValueError(
                "Observer used more than once in Experiment -> only 1 target per observer!"
            )

    def get_target_ids(self) -> list:
        return [_id for _config in self.target_configs for _id in _config.target_IDs]

    def get_target_config(self, target_id: int) -> TargetConfig:
        for _config in self.target_configs:
            if target_id in _config.target_IDs:
                return _config
        # gets already caught in target_config - but keep:
        raise ValueError(f"Target-ID {target_id} was not found in Experiment '{self.name}'")
