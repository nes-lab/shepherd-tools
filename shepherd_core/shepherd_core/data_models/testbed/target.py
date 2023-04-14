from datetime import datetime
from typing import List, Optional

from pydantic import Field, root_validator

from .mcu import MCU
from shepherd_core.data_models.model_fixture import Fixtures
from shepherd_core.data_models.model_shepherd import ShpModel

fixtures = Fixtures("target_fixture.yaml", "testbed.target")


class Target(ShpModel):

    name: str
    version: str
    description: str = ""

    comment: str = ""

    created: datetime = Field(default_factory=datetime.now)

    mcu1: MCU
    mcu2: Optional[MCU] = None
    # TODO: programming pins per mcu should be here

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
