from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import root_validator

from shepherd_core.data_models.model_fixture import Fixtures
from shepherd_core.data_models.model_shepherd import ShpModel

from .mcu import MCU

fixture_path = Path("target_fixture.yaml").resolve()
fixtures = Fixtures(fixture_path, "testbed.target")


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
