from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import constr
from pydantic import root_validator

from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("mcu_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.mcu")


class ProgrammerProtocol(str, Enum):
    SWD = "SWD"
    swd = "SWD"
    sbw = "SBW"
    jtag = "JTAG"
    uart = "UART"


class MCU(ShpModel, title="Microcontroller of the Target Node"):
    """meta-data representation of a testbed-component (physical object)"""

    uid: constr(to_lower=True, max_length=16)
    name: constr(max_length=32)
    description: str
    comment: Optional[str] = None

    platform: constr(max_length=32)
    core: constr(max_length=32)
    programmer: ProgrammerProtocol

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
