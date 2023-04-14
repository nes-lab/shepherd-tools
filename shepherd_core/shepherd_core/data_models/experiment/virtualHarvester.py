from enum import Enum

from ..model_shepherd import ShpModel
from ..model_fixture import Fixtures
from pydantic import confloat
from pydantic import conint
from pydantic import constr
from pydantic import root_validator

vharvesters = Fixtures("virtualHarvester_fixture.yaml", "VirtualHarvesters")


class DTypeEnum(str, Enum):
    ivsample = "ivsample"
    ivcurve = "ivcurve"
    isc_voc = "isc_voc"


class VirtualHarvester(ShpModel):
    # General Config
    name: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
    ) = "mppt_opt"

    datatype: DTypeEnum  # = DTypeEnum.ivcurve
    # ⤷ of input file

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

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = vharvesters.inheritance(values)
        if values["name"] == "neutral":
            raise ValueError("Resulting Harvester can't be neutral")
        print(f"VHrv-Inheritances: {chain}")
        return values

    @root_validator(pre=False)
    def post_adjust(cls, values: dict):
        # TODO
        return values

    def get_parameters(self):
        # TODO
        pass
