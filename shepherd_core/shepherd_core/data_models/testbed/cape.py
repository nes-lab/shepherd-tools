"""meta-data representation of a testbed-component (physical object)."""

from datetime import date
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import model_validator

from shepherd_core.data_models.base.content import IdInt
from shepherd_core.data_models.base.content import NameStr
from shepherd_core.data_models.base.content import SafeStr
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.testbed_client import tb_client


class TargetPort(str, Enum):
    """Options for choosing a target-port."""

    A = a = "A"
    B = b = "B"


class Cape(ShpModel, title="Shepherd-Cape"):
    """meta-data representation of a testbed-component (physical object)."""

    id: IdInt
    name: NameStr
    version: NameStr
    description: SafeStr
    comment: Optional[SafeStr] = None
    # TODO: wake_interval, calibration

    active: bool = True
    created: Union[date, datetime] = Field(default_factory=datetime.now)
    calibrated: Union[date, datetime, None] = None

    def __str__(self) -> str:
        return self.name

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return values
