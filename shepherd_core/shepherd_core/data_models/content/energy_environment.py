from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import PositiveFloat
from pydantic import constr
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel

fixture_path = Path(__file__).resolve().with_name("energy_environment_fixture.yaml")
fixtures = Fixtures(fixture_path, "content.EnergyEnvironment")


class EnergyDType(str, Enum):
    ivsample = "ivsample"
    ivcurve = "ivcurve"
    isc_voc = "isc_voc"


class EnergyEnvironment(ShpModel):
    """Recording of meta-data representation of a testbed-component"""

    uid: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
        max_length=16,
    )
    name: constr(max_length=32)
    description: Optional[str] = None
    comment: Optional[str] = None

    data_path: Path
    data_type: EnergyDType

    duration: PositiveFloat
    # TODO: add other key features like energy,

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
