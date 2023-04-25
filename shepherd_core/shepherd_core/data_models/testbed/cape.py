from datetime import datetime
from pathlib import Path

from pydantic import Field
from pydantic import root_validator

from ..model_fixture import Fixtures
from ..model_shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("cape_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.cape")


class Cape(ShpModel):
    name: str  # TODO: wouldn't a unique ID be better?
    version: str
    description: str = ""
    comment: str = ""

    created: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
