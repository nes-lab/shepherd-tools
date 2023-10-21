from pydantic import Field

from ..data_models import ShpModel
from .content import VirtualHarvesterConfig
from .content.virtual_source import LUT1D
from .content.virtual_source import LUT2D


@DeprecationWarning
class VirtualSourceDoc(ShpModel, title="Virtual Source (Documented, Testversion)"):
    # General Config
    name: str = Field(
        title="Name of Virtual Source",
        description="Slug to use this Name as later reference",
        default="neutral",
    )
    inherit_from: str = Field(
        description="Name of converter to derive defaults from",
        default="neutral",
    )

    enable_boost: bool = Field(
        description="If false -> V_intermediate becomes V_input, "
        "output-switch-hysteresis is still usable",
        default=False,
    )
    enable_buck: bool = Field(
        description="If false -> V_output becomes V_intermediate",
        default=False,
    )
    log_intermediate_voltage: bool = Field(
        description="Record / log virtual intermediate (cap-)voltage and "
        "-current (out) instead of output-voltage and -current",
        default=False,
    )

    interval_startup_delay_drain_ms: float = Field(
        description="Model begins running but Target is not draining the buffer",
        default=0,
        ge=0,
        le=10e3,
    )

    harvester: VirtualHarvesterConfig = Field(
        description="Only active / needed if input is 'ivcurves'",
        default=VirtualHarvesterConfig(name="mppt_opt"),
    )

    V_input_max_mV: float = Field(
        description="Maximum input Voltage [mV]",
        default=10_000,
        ge=0,
        le=10e3,
    )
    I_input_max_mA: float = Field(
        description="Maximum input Current [mA]",
        default=4_200,
        ge=0,
        le=4.29e3,
    )
    V_input_drop_mV: float = Field(
        title="Drop of Input-Voltage [mV]",
        description="Simulate an input-diode",
        default=0,
        ge=0,
        le=4.29e6,
    )
    R_input_mOhm: float = Field(
        description="Resistance only active with disabled boost, range [1 mOhm; 1MOhm]",
        default=0,
        ge=0,
        le=4.29e6,
    )

    C_intermediate_uF: float = Field(
        description="Capacity of primary Storage-Capacitor",
        default=0,
        ge=0,
        le=100_000,
    )
    V_intermediate_init_mV: float = Field(
        description="Allow a proper / fast startup",
        default=3_000,
        ge=0,
        le=10_000,
    )
    I_intermediate_leak_nA: float = Field(
        description="Current leakage of intermediate buffer capacitor",
        default=0,
        ge=0,
        le=4.29e9,
    )

    V_intermediate_enable_threshold_mV: float = Field(
        description="Target gets connected (hysteresis-combo with next value)",
        default=1,
        ge=0,
        le=10_000,
    )
    V_intermediate_disable_threshold_mV: float = Field(
        description="Target gets disconnected",
        default=0,
        ge=0,
        le=10_000,
    )
    interval_check_thresholds_ms: float = Field(
        description="Some BQs check every 64 ms if output should be disconnected",
        default=0,
        ge=0,
        le=4.29e3,
    )

    V_pwr_good_enable_threshold_mV: float = Field(
        description="Target is informed by pwr-good on output-pin (hysteresis) "
        "-> for intermediate voltage",
        default=2800,
        ge=0,
        le=10_000,
    )
    V_pwr_good_disable_threshold_mV: float = Field(
        description="Target is informed by pwr-good on output-pin (hysteresis) "
        "-> for intermediate voltage",
        default=2200,
        ge=0,
        le=10_000,
    )
    immediate_pwr_good_signal: bool = Field(
        description="1: activate instant schmitt-trigger, "
        "0: stay in interval for checking thresholds",
        default=True,
    )

    C_output_uF: float = Field(
        description="Final (always last) stage to compensate undetectable "
        "current spikes when enabling power for target",
        default=1.0,
        ge=0,
        le=4.29e6,
    )

    # Extra
    V_output_log_gpio_threshold_mV: float = Field(
        description="Min voltage needed to enable recording changes in gpio-bank",
        default=1400,
        ge=0,
        le=4.29e6,
    )

    # Boost Converter
    V_input_boost_threshold_mV: float = Field(
        description="min input-voltage for the boost converter to work",
        default=0,
        ge=0,
        le=10_000,
    )
    V_intermediate_max_mV: float = Field(
        description="Threshold for shutting off Boost converter",
        default=10_000,
        ge=0,
        le=10_000,
    )

    LUT_input_efficiency: LUT2D = Field(
        description="# input-array[12][12] depending on "
        "array[inp_voltage][log(inp_current)], "
        "influence of cap-voltage is not implemented",
        default=12 * [12 * [1.00]],
    )
    LUT_input_V_min_log2_uV: int = Field(
        description="Example: n=7, 2^n = 128 uV -> array[0] is for inputs < 128 uV",
        default=0,
        ge=0,
        le=20,
    )
    LUT_input_I_min_log2_nA: int = Field(
        description="Example: n=8, 2^n = 256 nA -> array[0] is for inputs < 256 nA",
        default=0,
        ge=0,
        le=20,
    )

    # Buck Converter
    V_output_mV: float = Field(
        description="Fixed Voltage of Buck-Converter (as long as "
        "Input is > Output + Drop-Voltage)",
        default=2400,
        ge=0,
        le=5_000,
    )
    V_buck_drop_mV: float = Field(
        description="Simulate LDO min voltage differential or output-diode",
        default=0,
        ge=0,
        le=5_000,
    )

    LUT_output_efficiency: LUT1D = Field(
        description="Output-Array[12] depending on output_current. In & Output is linear",
        default=12 * [1.00],
    )
    LUT_output_I_min_log2_nA: int = Field(
        description="Example: n=8, 2^n = 256 nA -> array[0] is for inputs < 256 nA, "
        "see notes on LUT_input for explanation",
        default=0,
        ge=0,
        le=20,
    )
