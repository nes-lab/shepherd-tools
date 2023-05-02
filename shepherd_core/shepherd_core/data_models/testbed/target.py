from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import conint
from pydantic import root_validator

from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .mcu import MCU

fixture_path = Path(__file__).resolve().with_name("target_fixture.yaml")
fixtures = Fixtures(fixture_path, "target")

id_int16 = conint(ge=0, lt=2**16)


class Target(ShpModel, title="Target Node (DuT)"):
    """meta-data representation of a testbed-component (physical object)"""

    id: id_int16  # noqa: A003
    name: name_str
    version: name_str
    description: safe_str

    comment: Optional[safe_str] = None

    created: datetime = Field(default_factory=datetime.now)

    mcu1: Union[MCU, name_str]
    mcu2: Union[MCU, name_str, None] = None
    #

    # TODO programming pins per mcu should be here (or better in Cape)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values

    @root_validator(pre=False)
    def post_correction(cls, values: dict) -> dict:
        if isinstance(values["mcu1"], str):
            values["mcu1"] = MCU(name=values["mcu1"])
            # ⤷ this will raise if default is faulty
        if isinstance(values["mcu2"], str):
            values["mcu2"] = MCU(name=values["mcu2"])
        return values
