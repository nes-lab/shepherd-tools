from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import confloat
from pydantic import conint
from pydantic import root_validator

from ..base.content import IdInt
from ..base.content import NameStr
from ..base.content import SafeStr
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

    id: IdInt  # noqa: A003
    name: NameStr
    description: SafeStr
    comment: Optional[SafeStr] = None

    platform: NameStr
    core: NameStr
    prog_protocol: ProgrammerProtocol
    prog_voltage: confloat(ge=1, le=5) = 3
    prog_datarate: conint(gt=0, le=1_000_000) = 500_000

    fw_name_default: str
    # ⤷ can't be FW-Object (circular import)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def query_database(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, _ = fixtures.inheritance(values)
        return values
