from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import constr
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel

fixture_path = Path(__file__).resolve().with_name("cape_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.cape")


class Cape(ShpModel, title="Shepherd-Cape"):
    """meta-data representation of a testbed-component (physical object)"""

    uid: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
        max_length=16,
    )

    name: constr(max_length=32)
    version: constr(max_length=32)
    description: str
    comment: Optional[str] = None

    created: datetime = Field(default_factory=datetime.now)
    calibrated: datetime

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
