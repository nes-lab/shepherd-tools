from enum import Enum
from pathlib import Path

from pydantic import PositiveFloat
from pydantic import root_validator

from ...testbed_client import tb_client
from ..base.content import ContentModel


class EnergyDType(str, Enum):
    ivsample = "ivsample"
    ivsamples = "ivsample"
    ivcurve = "ivcurve"
    ivcurves = "ivcurve"
    isc_voc = "isc_voc"


class EnergyEnvironment(ContentModel):
    """Recording of meta-data representation of a testbed-component"""

    # General Metadata & Ownership -> ContentModel

    data_path: Path
    data_type: EnergyDType

    duration: PositiveFloat
    energy_Ws: PositiveFloat
    valid: bool = False

    # TODO: scale up/down voltage/current

    @root_validator(pre=True)
    def query_database(cls, values: dict) -> dict:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        values = tb_client.fill_in_user_data(values)
        return values
