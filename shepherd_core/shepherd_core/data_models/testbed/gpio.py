from pathlib import Path
from typing import Optional

import yaml
from pydantic import root_validator
from strenum import StrEnum

from .. import Fixtures
from .. import ShpModel
from ..model_shepherd import repr_str

fixture_path = Path(__file__).resolve().with_name("gpio_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.gpio")


class Direction(StrEnum):
    IN = "Input"
    OUT = "Output"
    IO = "Bidirectional"  # TODO: probably the other way around


yaml.add_representer(Direction, repr_str)


class GPIO(ShpModel):
    name: str
    description: Optional[str] = None
    comment: Optional[str] = None

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
