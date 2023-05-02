from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import conint
from pydantic import constr
from pydantic import root_validator

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("gpio_fixture.yaml")
fixtures = Fixtures(fixture_path, "gpio")


class Direction(str, Enum):
    Input = "IN"
    IN = "IN"
    Output = "OUT"
    OUT = "OUT"
    Bidirectional = "IO"
    IO = "IO"


class GPIO(ShpModel, title="GPIO of Observer Node"):
    """meta-data representation of a testbed-component"""

    id: id_int  # noqa: A003
    name: name_str
    description: Optional[safe_str] = None
    comment: Optional[safe_str] = None

    direction: Direction = Direction.Input
    dir_switch: Optional[constr(max_length=32)]

    reg_pru: Optional[constr(max_length=10)] = None
    pin_pru: Optional[constr(max_length=10)] = None
    reg_sys: Optional[conint(ge=0)] = None
    pin_sys: Optional[constr(max_length=10)] = None

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        # ensure that either pru or sys is used, otherwise instance is considered faulty
        no_pru = (values["reg_pru"] is None) or (values["pin_pru"] is None)
        no_sys = (values["reg_sys"] is None) or (values["pin_sys"] is None)
        if no_pru and no_sys:
            raise ValueError(
                f"GPIO-Instance is faulty -> it needs to use pru or sys, content: {values}"
            )
        return values

    def user_controllable(self) -> bool:
        return ("gpio" in self.name.lower()) and (self.direction in ["IO", "OUT"])
