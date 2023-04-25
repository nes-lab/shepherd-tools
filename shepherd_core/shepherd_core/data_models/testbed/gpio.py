from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import root_validator

from ..model_fixture import Fixtures
from ..model_shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("gpio_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.gpio")


class Direction(str, Enum):
    IN = "Input"
    OUT = "Output"
    IO = "Bidirectional"  # TODO: probably the other way around


class GPIO(ShpModel):
    name: str
    description: str = ""
    comment: str = ""

    direction: Direction = Direction.IN
    dir_switch: Optional[str]

    reg_pru: str = ""  # TODO: these also optional instead of ""?
    pin_pru: str = ""
    reg_sys: str = ""
    pin_sys: str = ""

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
