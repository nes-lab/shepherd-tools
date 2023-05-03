from pathlib import Path

from pydantic import confloat
from pydantic import conint
from pydantic import root_validator

from ...logger import logger
from ..base.content import ContentModel
from ..base.fixture import Fixtures
from .energy_environment import EnergyDType

fixture_path = Path(__file__).resolve().with_name("virtual_harvester_fixture.yaml")
fixtures = Fixtures(fixture_path, "VirtualHarvester")


class VirtualHarvester(ContentModel, title="Config for the Harvester"):
    """A Harvester is needed when the file-based energy environment
    of the virtual source is not already supplied as ivsamples"""

    # General Metadata & Ownership -> ContentModel

    datatype: EnergyDType = EnergyDType.ivsample
    # ⤷ of output

    window_size: conint(ge=8, le=2_000) = 8  # TODO: min was 16

    voltage_mV: confloat(ge=0, le=5_000) = 2_500
    # ⤷ starting-point for some algorithms (mppt_po)
    voltage_min_mV: confloat(ge=0, le=5_000) = 0
    voltage_max_mV: confloat(ge=0, le=5_000) = 5_000
    current_limit_uA: confloat(ge=1, le=50_000) = 50_000
    # ⤷ allows to keep trajectory in special region (or constant current tracking)
    # ⤷ boundary for detecting open circuit in emulated version (working on IV-Curves)
    # TODO: min = 10**6 * self._cal.convert_raw_to_value("harvester", "adc_current", 4)
    voltage_step_mV: confloat(ge=1, le=1_000_000) = 1
    # TODO: min = 10**3 * self._cal.convert_raw_to_value("harvester", "dac_voltage_b", 4)

    setpoint_n: confloat(ge=0, le=1.0) = 0.70
    interval_ms: confloat(ge=0.01, le=1_000_000) = 100
    # ⤷ between start of measurements
    duration_ms: confloat(ge=0.01, le=1_000_000) = 0.1
    # ⤷ of measurement
    rising: bool = True
    # ⤷ direction of sawtooth

    # Underlying recoder
    wait_cycles: conint(ge=0, le=100) = 1
    # ⤷ first cycle: ADC-Sampling & DAC-Writing, further steps: waiting

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        if values["name"] == "neutral":
            raise ValueError("Resulting Harvester can't be neutral")
        logger.debug("VHrv-Inheritances: %s", chain)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        # TODO: port it over
        return values
