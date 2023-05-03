from datetime import date
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import root_validator

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("cape_fixture.yaml")
fixtures = Fixtures(fixture_path, "cape")


class TargetPort(str, Enum):
    A = "A"
    B = "B"


class Cape(ShpModel, title="Shepherd-Cape"):
    """meta-data representation of a testbed-component (physical object)"""

    id: id_int  # noqa: A003
    name: name_str
    version: name_str
    description: safe_str
    comment: Optional[safe_str] = None
    # TODO: wake_interval, calibration

    created: Union[date, datetime] = Field(default_factory=datetime.now)
    calibrated: Union[date, datetime, None] = None

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
