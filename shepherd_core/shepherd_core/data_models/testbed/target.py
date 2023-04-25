from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import root_validator

from ..model_fixture import Fixtures
from ..model_shepherd import ShpModel
from .mcu import MCU

fixture_path = Path(__file__).resolve().with_name("target_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.target")


class Target(ShpModel):
    name: str
    version: str
    description: str
    # TODO: unique ID, sequential ID, backwards_ref for cape, observer, emu

    comment: Optional[str] = None

    created: datetime = Field(default_factory=datetime.now)

    mcu1: MCU
    mcu2: Optional[MCU] = None

    firmware1: Union[Path, str]
    firmware2: Union[Path, str, None] = None

    # TODO: programming pins per mcu should be here (or better in Cape)
    # TODO: firmware should be handled here

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
