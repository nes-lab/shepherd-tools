from pathlib import Path

from pydantic import confloat
from pydantic import conint
from pydantic import root_validator

from ...commons import samplerate_sps_default
from ...logger import logger
from ..base.calibration import CalibrationHarvester
from ..base.content import ContentModel
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .energy_environment import EnergyDType

fixture_path = Path(__file__).resolve().with_name("virtual_harvester_fixture.yaml")
fixtures = Fixtures(fixture_path, "VirtualHarvester")


class VirtualHarvester(ContentModel, title="Config for the Harvester"):
    """A Harvester is needed when the file-based energy environment
    of the virtual source is not already supplied as ivsamples
    TODO: Should be named -Config internally
    """

    # General Metadata & Ownership -> ContentModel

    datatype: EnergyDType = EnergyDType.ivsample
    # ⤷ of output

    window_size: conint(ge=8, le=2_000) = 8  # TODO: min was 16, TEST

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

    # internal states
    inheritance_chain: list = []

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        if values["name"] == "neutral":
            raise ValueError("Resulting Harvester can't be neutral")
        logger.debug("VHrv-Inheritances: %s", chain)
        values[
            "inheritance_chain"
        ] = chain  # TODO: not clean for transitioning to testbed

        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if values["voltage_min_mV"] > values["voltage_max_mV"]:
            raise ValueError("Voltage min > max")
        if values["voltage_mV"] < values["voltage_min_mV"]:
            raise ValueError("Voltage below min")
        if values["voltage_mV"] > values["voltage_max_mV"]:
            raise ValueError("Voltage above max")

        # TODO: port it over
        cal = CalibrationHarvester()  # todo: as argument?
        values["current_limit_uA"] = max(
            10**6 * cal.adc_C_Hrv.raw_to_si(4), values["current_limit_uA"]
        )

        if "voltage_step_mV" not in values:
            values["voltage_step_mV"] = (
                abs(values["voltage_max_mV"] - values["voltage_min_mV"])
                / values["window_size"]
            )

        values["voltage_step_mV"] = max(
            10**3 * cal.dac_V_Hrv.raw_to_si(4), values["voltage_step_mV"]
        )

        return values

    def calc_hrv_mode(self, for_emu: bool) -> int:
        return 1 * int(for_emu) + 2 * self.rising

    def calc_algorithm_num(self, for_emu: bool) -> int:
        num = 0
        for base in self.inheritance_chain:
            if base in algorithms:
                num += algorithms[base]
        if for_emu and num <= algorithms["ivcurve"]:
            raise ValueError(
                f"[{self.name}] Select valid harvest-algorithm for emulator, "
                f"current usage = {self.inheritance_chain}",
            )
        elif num < algorithms["isc_voc"]:
            raise ValueError(
                f"[{self.name}] Select valid harvest-algorithm for harvester, "
                f"current usage = {self.inheritance_chain}",
            )
        return num


u32 = conint(ge=0, lt=2**32)


# Currently implemented harvesters
# NOTE: numbers have meaning and will be tested ->
# - harvesting on "neutral" is not possible
# - emulation with "ivcurve" or lower is also resulting in Error
# - "_opt" has its own algo for emulation, but is only a fast mppt_po for harvesting
algorithms = {
    "neutral": 2**0,
    "isc_voc": 2**3,
    "ivcurve": 2**4,
    "cv": 2**8,
    "cv20": 2**8,
    # "ci": 2**9, # is this desired?
    "mppt_voc": 2**12,
    "mppt_po": 2**13,
    "mppt_opt": 2**14,
}


class VirtualHarvesterPRU(ShpModel):
    algorithm: u32
    hrv_mode: u32
    window_size: u32
    voltage_uV: u32
    voltage_min_uV: u32
    voltage_max_uV: u32
    voltage_step_uV: u32
    # ⤷ for window-based algo like ivcurve
    current_limit_nA: u32
    # ⤷ lower bound to detect zero current
    setpoint_n8: u32
    interval_n: u32
    # ⤷ between measurements
    duration_n: u32
    # ⤷ of measurement
    wait_cycles_n: u32
    # ⤷ for DAC to settle

    @classmethod
    def from_vhrv(cls, data: VirtualHarvester, for_emu: bool = False):
        return cls(
            algorithm=data.calc_algorithm_num(for_emu),
            hrv_mode=data.calc_hrv_mode(for_emu),
            window_size=data.window_size,  # TODO: emu gets window_samples
            voltage_uV=data.voltage_mV * 10**3,
            voltage_min_uV=data.voltage_min_mV * 10**3,
            voltage_max_uV=data.voltage_max_mV * 10**3,
            voltage_step_uV=data.voltage_step_mV * 10**3,
            current_limit_nA=data.current_limit_uA * 10**3,
            setpoint_n8=min(255, data.setpoint_n * 2**8),
            interval_n=data.interval_ms * samplerate_sps_default * 1e-3,
            duration_n=data.duration_ms * samplerate_sps_default * 1e-3,
            wait_cycles_n=data.wait_cycles,
        )
