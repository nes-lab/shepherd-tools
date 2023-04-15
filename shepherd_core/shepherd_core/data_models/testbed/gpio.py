from enum import Enum
from pathlib import Path

from pydantic import root_validator

from shepherd_core.data_models.model_fixture import Fixtures
from shepherd_core.data_models.model_shepherd import ShpModel

fixture_path = Path("gpio_fixture.yaml").resolve()
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
    dir_switch: str

    reg_pru = str
    pin_pru = str
    reg_sys = str
    pin_sys = str

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
