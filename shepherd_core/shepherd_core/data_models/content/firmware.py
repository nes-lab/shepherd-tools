from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import constr
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel
from ..testbed.mcu import MCU

fixture_path = Path(__file__).resolve().with_name("firmware_fixture.yaml")
fixtures = Fixtures(fixture_path, "content.firmware")


class FirmwareDType(str, Enum):
    base64_hex = "hex"
    base64_elf = "elf"
    path_hex = "path_hex"
    path_elf = "path_elf"


class Firmware(ShpModel, title="Firmware of Target"):
    """meta-data representation of a data-component"""

    uid: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
        max_length=16,
    )
    name: constr(max_length=32)
    description: Optional[
        str
    ] = None  # TODO: should not be optional for content (open2group/all)
    comment: Optional[str] = None

    mcu: MCU
    data: Union[constr(min_length=3, max_length=1_000_000), Path]
    # ⤷ local str-length constraints overrule global ones!
    data_type: FirmwareDType

    # internal, TODO: together with uid these vars could be become a new template class for content
    owner: constr(max_length=32)
    group: constr(max_length=32)
    open2group: bool = False
    open2all: bool = False
    created: datetime = Field(default_factory=datetime.now)

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
