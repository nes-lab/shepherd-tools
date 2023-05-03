from enum import Enum
from pathlib import Path

from pydantic import PositiveFloat
from pydantic import root_validator

from ..base.content import ContentModel
from ..base.fixture import Fixtures

fixture_path = Path(__file__).resolve().with_name("energy_environment_fixture.yaml")
fixtures = Fixtures(fixture_path, "EnergyEnvironment")


class EnergyDType(str, Enum):
    ivsample = "ivsample"
    ivcurve = "ivcurve"
    isc_voc = "isc_voc"


class EnergyEnvironment(ContentModel):
    """Recording of meta-data representation of a testbed-component"""

    # General Metadata & Ownership -> ContentModel

    data_path: Path
    data_type: EnergyDType

    duration: PositiveFloat
    energy_Ws: PositiveFloat
    valid: bool = False

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
