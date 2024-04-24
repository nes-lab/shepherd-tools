"""meta-data representation of a testbed-component (physical object)."""

from datetime import date
from datetime import datetime
from enum import Enum
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import model_validator

from ...testbed_client import tb_client
from ..base.content import IdInt
from ..base.content import NameStr
from ..base.content import SafeStr
from ..base.shepherd import ShpModel


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
    def query_database(cls, values: dict) -> dict:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return values
