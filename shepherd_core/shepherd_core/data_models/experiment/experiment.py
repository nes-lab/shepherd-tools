"""Config for testbed experiments."""

from collections.abc import Iterable
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from typing import Optional

from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self
from typing_extensions import deprecated

from shepherd_core.config import config
from shepherd_core.data_models.base.content import IdInt
from shepherd_core.data_models.base.content import NameStr
from shepherd_core.data_models.base.content import SafeStr
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.timezone import local_now
from shepherd_core.data_models.testbed.target import Target
from shepherd_core.data_models.testbed.testbed import Testbed
from shepherd_core.version import version

from .observer_features import SystemLogging
from .target_config import TargetConfig

# defaults (pre-init complex types)
sys_log_all = SystemLogging()  # = all active


class Experiment(ShpModel, title="Config of an Experiment"):
    """Config for experiments on the testbed emulating energy environments for target nodes."""

    # General Properties
    name: NameStr
    description: Annotated[
        Optional[SafeStr], Field(description="Required for public instances")
    ] = None
    comment: Optional[SafeStr] = None

    # feedback
    email_results: bool = True

    sys_logging: SystemLogging = sys_log_all

    # schedule
    time_start: Optional[datetime] = None  # = ASAP
    duration: Optional[timedelta] = None  # = till EOF

    # targets
    target_configs: Annotated[list[TargetConfig], Field(min_length=1, max_length=128)]

    # debug
    lib_ver: Optional[str] = version

    # deprecated fields, TODO: remove before public release
    id: Annotated[Optional[int], deprecated("not needed")] = None
    created: Annotated[Optional[datetime], deprecated("not needed")] = None
    abort_on_error: Annotated[bool, deprecated("has no effect")] = False
    owner_id: Annotated[Optional[IdInt], deprecated("not needed")] = None

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        self._validate_observers(self.target_configs)
        self._validate_targets(self.target_configs)
        if self.duration and self.duration.total_seconds() < 0:
            raise ValueError("Duration of experiment can't be negative.")
        return self

    @staticmethod
    def _validate_targets(configs: Iterable[TargetConfig]) -> None:
        target_ids: list[int] = []
        custom_ids: list[int] = []
        for _config in configs:
            for _id in _config.target_IDs:
                target_ids.append(_id)
                if config.VALIDATE_INFRA:
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
    def _validate_observers(configs: Iterable[TargetConfig]) -> None:
        if not config.VALIDATE_INFRA:
            return
        testbed = Testbed()
        target_ids = [_id for _config in configs for _id in _config.target_IDs]
        obs_ids = [testbed.get_observer(_id).id for _id in target_ids]
        if len(target_ids) > len(set(obs_ids)):
            raise ValueError(
                "Observer is used more than once in Experiment -> only 1 target per observer!"
            )

    def get_target_ids(self) -> list:
        return [_id for _config in self.target_configs for _id in _config.target_IDs]

    def get_target_config(self, target_id: int) -> TargetConfig:
        for _config in self.target_configs:
            if target_id in _config.target_IDs:
                return _config
        # gets already caught in target_config - but keep:
        msg = f"Target-ID {target_id} was not found in Experiment '{self.name}'"
        raise ValueError(msg)

    def folder_name(self, custom_date: Optional[datetime] = None) -> str:
        date = custom_date if custom_date is not None else self.time_start
        timestamp = local_now() if date is None else date
        timestrng = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        # ⤷ closest to ISO 8601, avoids ":"
        return f"{timestrng}_{self.name.replace(' ', '_')}"
