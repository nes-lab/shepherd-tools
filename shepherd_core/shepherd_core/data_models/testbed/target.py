from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import conint
from pydantic import constr
from pydantic import root_validator

from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .mcu import MCU

fixture_path = Path(__file__).resolve().with_name("target_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.target")


class Target(ShpModel, title="Target Node (DuT)"):
    """meta-data representation of a testbed-component (physical object)"""

    id: conint(ge=0, lt=2**16)  # noqa: A003
    name: constr(max_length=32)
    version: constr(max_length=32)
    description: str

    comment: Optional[str] = None

    created: datetime = Field(default_factory=datetime.now)

    mcu1: MCU
    mcu2: Optional[MCU] = None

    # TODO programming pins per mcu should be here (or better in Cape)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict):
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
