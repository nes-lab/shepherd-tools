from datetime import datetime

from pydantic import Field, root_validator

from shepherd_core.data_models.model_fixture import Fixtures
from shepherd_core.data_models.model_shepherd import ShpModel

fixtures = Fixtures("cape_fixture.yaml", "testbed.cape")


class Cape(ShpModel):

    name: str
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
