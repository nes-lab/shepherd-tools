from pathlib import Path
from typing import Optional

import yaml
from pydantic import constr
from pydantic import root_validator
from strenum import StrEnum

from .. import Fixtures
from .. import ShpModel
from ..model_shepherd import repr_str

fixture_path = Path(__file__).resolve().with_name("gpio_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.gpio")


class Direction(StrEnum):
    Input = "IN"
    IN = "IN"
    Output = "OUT"
    OUT = "OUT"
    Bidirectional = "IO"
    IO = "IO"


yaml.add_representer(Direction, repr_str)


class GPIO(ShpModel):
    uid: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
        max_length=16,
    )

    name: constr(max_length=32)
    description: Optional[str] = None
    comment: Optional[str] = None

    direction: Direction = Direction.Input
    dir_switch: Optional[constr(max_length=32)]

    reg_pru: Optional[constr(max_length=10)] = None
    pin_pru: Optional[constr(max_length=10)] = None
    reg_sys: Optional[int] = None
    pin_sys: Optional[constr(max_length=10)] = None

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
