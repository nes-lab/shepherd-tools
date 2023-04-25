from enum import Enum
from pathlib import Path

from pydantic import root_validator

from ..model_fixture import Fixtures
from ..model_shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("mcu_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.mcu")


class Programmer(str, Enum):
    swd = "SWD"
    sbw = "SBW"
    jtag = "JTAG"
    uart = "UART"


class MCU(ShpModel):
    name: str
    description: str = ""
    comment: str = ""

    platform: str
    core: str
    programmer: Programmer

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
