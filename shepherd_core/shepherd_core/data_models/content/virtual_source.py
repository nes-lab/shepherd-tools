from pathlib import Path

from pydantic import confloat
from pydantic import conint
from pydantic import conlist
from pydantic import root_validator

from ...logger import logger
from ..base.content import ContentModel
from ..base.fixture import Fixtures
from .energy_environment import EnergyDType
from .virtual_harvester import VirtualHarvester

fixture_path = Path(__file__).resolve().with_name("virtual_source_fixture.yaml")
fixtures = Fixtures(fixture_path, "VirtualSource")


class VirtualSource(ContentModel, title="Config for the virtual Source"):
    """The virtual Source uses the energy environment (file)
    for supplying the Target Node during the experiment.
    If not already done, the energy will be harvested and then converted.
    The converter-stage is software defined and offers:
      buck-boost-combinations,
      a simple diode + resistor and
      an intermediate buffer capacitor."""

    # General Metadata & Ownership -> ContentModel

    enable_boost: bool = False
    enable_buck: bool = False

    interval_startup_delay_drain_ms: confloat(ge=0, le=10e3) = 0

    harvester: VirtualHarvester = VirtualHarvester(name="mppt_opt")

    V_input_max_mV: confloat(ge=0, le=10e3) = 10_000
    I_input_max_mA: confloat(ge=0, le=4.29e3) = 4_200
    V_input_drop_mV: confloat(ge=0, le=4.29e6) = 0
    R_input_mOhm: confloat(ge=0, le=4.29e6) = 0

    C_intermediate_uF: confloat(ge=0, le=100_000) = 0
    V_intermediate_init_mV: confloat(ge=0, le=10_000) = 3_000
    I_intermediate_leak_nA: confloat(ge=0, le=4.29e9) = 0

    V_intermediate_enable_threshold_mV: confloat(ge=0, le=10_000) = 1
    V_intermediate_disable_threshold_mV: confloat(ge=0, le=10_000) = 0
    interval_check_thresholds_ms: confloat(ge=0, le=4.29e3) = 0

    V_pwr_good_enable_threshold_mV: confloat(ge=0, le=10_000) = 2_800
    V_pwr_good_disable_threshold_mV: confloat(ge=0, le=10_000) = 2200
    immediate_pwr_good_signal: bool = True

    C_output_uF: confloat(ge=0, le=4.29e6) = 1.0

    # Extra
    V_output_log_gpio_threshold_mV: confloat(ge=0, le=4.29e6) = 1_400

    # Boost Converter
    V_input_boost_threshold_mV: confloat(ge=0, le=10_000) = 0
    V_intermediate_max_mV: confloat(ge=0, le=10_000) = 10_000

    LUT_input_efficiency: conlist(
        item_type=conlist(confloat(ge=0.0, le=1.0), min_items=12, max_items=12),
        min_items=12,
        max_items=12,
    ) = 12 * [12 * [1.00]]
    LUT_input_V_min_log2_uV: conint(ge=0, le=20) = 0
    LUT_input_I_min_log2_nA: conint(ge=0, le=20) = 0

    # Buck Converter
    V_output_mV: confloat(ge=0, le=5_000) = 2_400
    V_buck_drop_mV: confloat(ge=0, le=5_000) = 0

    LUT_output_efficiency: conlist(
        item_type=confloat(ge=0.0, le=1.0),
        min_items=12,
        max_items=12,
    ) = 12 * [1.00]
    LUT_output_I_min_log2_nA: conint(ge=0, le=20) = 0

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        logger.debug("VSrc-Inheritances: %s", chain)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if values["harvester"].datatype != EnergyDType.ivsample:
            raise ValueError(
                f"Harvester '{values['harvester'].name}' of "
                f"Source '{values['name']}' must output iv-samples for emulation "
                f"(but is '{values['harvester'].datatype}')"
            )
        # TODO: port rest over
        return values
