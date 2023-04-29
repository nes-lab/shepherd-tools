from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import constr
from pydantic import root_validator

from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("cape_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.cape")


class Cape(ShpModel, title="Shepherd-Cape"):
    """meta-data representation of a testbed-component (physical object)"""

    uid: constr(to_lower=True, max_length=16)
    name: constr(max_length=32)
    version: constr(max_length=32)
    description: str
    comment: Optional[str] = None

    created: Union[date, datetime] = Field(default_factory=datetime.now)
    calibrated: Union[date, datetime, None] = None

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
