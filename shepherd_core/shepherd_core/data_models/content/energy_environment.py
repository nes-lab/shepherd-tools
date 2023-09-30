from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import PositiveFloat
from pydantic import model_validator

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
    data_local: bool = True
    # ⤷ signals that file has to be copied to testbed

    duration: PositiveFloat
    energy_Ws: PositiveFloat
    valid: bool = False

    # TODO: scale up/down voltage/current

    # additional descriptive metadata
    light_source: Optional[str] = None
    weather_conditions: Optional[str] = None
    indoor: Optional[bool] = None
    location: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict) -> dict:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        # TODO: figure out a way to crosscheck type with actual data
        return tb_client.fill_in_user_data(values)
