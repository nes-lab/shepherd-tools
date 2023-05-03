from enum import Enum
from pathlib import Path
from typing import Union

from pydantic import constr
from pydantic import root_validator

from ..base.content import ContentModel
from ..base.fixture import Fixtures
from ..testbed.mcu import MCU

fixture_path = Path(__file__).resolve().with_name("firmware_fixture.yaml")
fixtures = Fixtures(fixture_path, "firmware")


class FirmwareDType(str, Enum):
    base64_hex = "hex"
    base64_elf = "elf"
    path_hex = "path_hex"
    path_elf = "path_elf"


class Firmware(ContentModel, title="Firmware of Target"):
    """meta-data representation of a data-component"""

    # General Metadata & Ownership -> ContentModel

    mcu: MCU

    data: Union[constr(min_length=3, max_length=1_000_000), Path]
    data_type: FirmwareDType

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
