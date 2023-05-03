from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import confloat
from pydantic import conint
from pydantic import root_validator

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel

fixture_path = Path(__file__).resolve().with_name("mcu_fixture.yaml")
fixtures = Fixtures(fixture_path, "mcu")


class ProgrammerProtocol(str, Enum):
    SWD = "SWD"
    swd = "SWD"
    sbw = "SBW"
    jtag = "JTAG"
    uart = "UART"


class MCU(ShpModel, title="Microcontroller of the Target Node"):
    """meta-data representation of a testbed-component (physical object)"""

    id: id_int  # noqa: A003
    name: name_str
    description: safe_str
    comment: Optional[safe_str] = None

    platform: name_str
    core: name_str
    prog_protocol: ProgrammerProtocol
    prog_voltage: confloat(ge=1, le=5) = 3
    prog_datarate: conint(gt=0, le=1_000_000) = 500_000

    fw_name_default: str
    # ⤷ can't be FW-Object (circular import)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
