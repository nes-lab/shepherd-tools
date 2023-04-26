from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import conint
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel
from .firmware import Firmware
from .mcu import MCU

fixture_path = Path(__file__).resolve().with_name("target_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.target")


class Target(ShpModel):
    uid: conint(ge=0, lt=2**16)
    name: str
    version: str
    description: str
    # TODO: unique ID, sequential ID, backwards_ref for cape, observer, emu

    comment: Optional[str] = None

    created: datetime = Field(default_factory=datetime.now)

    mcu1: MCU
    mcu2: Optional[MCU] = None

    firmware1: Firmware
    firmware2: Optional[Firmware] = None

    # TODO programming pins per mcu should be here (or better in Cape)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        # TODO: test for matching FW
        return values
