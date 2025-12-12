"""Generalized virtual source data models."""

from typing import Annotated
from typing import Any

from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client

from .energy_environment import EnergyDType
from .virtual_harvester_config import HarvesterPRUConfig
from .virtual_harvester_config import VirtualHarvesterConfig
from .virtual_storage_config import VirtualStorageConfig

# Custom Types
LUT_SIZE: int = 12
NormedNum = Annotated[float, Field(ge=0.0, le=1.0)]
LUT1D = Annotated[list[NormedNum], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]
LUT2D = Annotated[list[LUT1D], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]

# defaults (pre-init complex types for improved perf) TODO: is documentation still fine?
vhrv_mppt_opt = VirtualHarvesterConfig(name="mppt_opt")


class VirtualSourceConfig(ContentModel, title="Config for the virtual Source"):
    """The vSrc uses the energy environment (file) for supplying the Target Node.

    If not already done, the energy will be harvested and
    then converted during the experiment.

    The converter-stage is software defined and offers:
    - buck-boost-combinations,
    - a simple diode + resistor and
    - an intermediate storage capacitor.
    """

    # TODO: I,V,R should be in regular unit (V, A, Ohm)

    # General Metadata & Ownership -> ContentModel

    enable_boost: bool = False
    """ ⤷ if false -> v_intermediate = v_input, output-switch-hysteresis is still usable"""
    enable_buck: bool = False
    """ ⤷ if false -> v_output = v_intermediate"""
    enable_feedback_to_hrv: bool = False
    """ Source can control a cv-harvester for ivsurface.
     Feedback is essential for some harvesters, i.e. diode-circuitry.
    """

    interval_startup_delay_drain_ms: Annotated[float, Field(ge=0, le=10_000)] = 0
    """ ⤷ Model begins running, but Target is not draining the storage capacitor
    until this delay is over.
    """

    harvester: VirtualHarvesterConfig = vhrv_mppt_opt
    """ ⤷ Only active / needed if input is ivsurface. """

    V_input_max_mV: Annotated[float, Field(ge=0, le=10_000)] = 10_000
    """ ⤷ Maximum input Voltage [mV] -> will be clipped."""
    I_input_max_mA: Annotated[float, Field(ge=0, le=4.29e3)] = 4_200
    """ ⤷ Maximum input Current [mA] -> will be clipped."""
    V_input_drop_mV: Annotated[float, Field(ge=0, le=4.29e6)] = 0
    """ ⤷ simulate voltage drop for input-diode or LDO."""
    R_input_mOhm: Annotated[float, Field(ge=0, le=4.29e6)] = 0
    """ ⤷ resistance only active with disabled boost, range [1 mOhm; 1MOhm]"""

    storage: VirtualStorageConfig | None = None
    """ ⤷ primary intermediate energy storage between boost- and buck-converter stage.
    Selecting "None" disables the storage and directly connects input to output.
    """
    V_intermediate_enable_output_threshold_mV: Annotated[float, Field(ge=0, le=10_000)] = 1
    """ ⤷ target gets connected (hysteresis-combo with next value)"""
    V_intermediate_disable_output_threshold_mV: Annotated[float, Field(ge=0, le=10_000)] = 0
    """ ⤷ target gets disconnected"""
    interval_check_thresholds_ms: Annotated[float, Field(ge=0, le=4.29e3)] = 0
    """ ⤷ some ICs (BQ) check every 64 ms if output should be disconnected"""
    # TODO: add intervals for input-disable, output-disable & power-good-signal

    V_pwr_good_enable_threshold_mV: Annotated[float, Field(ge=0, le=10_000)] = 2_800
    """ pwr-good: target is informed on output-pin (hysteresis)
     -> reference is the intermediate voltage """
    V_pwr_good_disable_threshold_mV: Annotated[float, Field(ge=0, le=10_000)] = 2200
    immediate_pwr_good_signal: bool = True
    """ ⤷ 1: activate instant schmitt-trigger, 0: stay in interval for checking thresholds"""

    C_output_uF: Annotated[float, Field(ge=0, le=4.29e6)] = 1.0
    """
    final (always last) stage to compensate undetectable current spikes when
    enabling power for target
    """
    # TODO: C_output is handled internally as delta-V, but should be a I_transient
    #       that makes it visible in simulation as additional i_out_drain
    # TODO: potential weakness, ACD lowpass is capturing transient,
    #       but energy is LOST with this model

    # Extra
    V_output_log_gpio_threshold_mV: Annotated[float, Field(ge=0, le=4.29e6)] = 1_400
    """ ⤷ minimum voltage threshold needed to enable recording changes in gpio-bank"""

    # Boost Converter
    V_input_boost_threshold_mV: Annotated[float, Field(ge=0, le=10_000)] = 0
    """ ⤷ minimum input-voltage for the boost converter to work"""
    V_intermediate_max_mV: Annotated[float, Field(ge=0, le=10_000)] = 10_000
    """ ⤷ threshold for shutting off boost converter """

    LUT_input_efficiency: LUT2D = 12 * [12 * [1.00]]
    """ ⤷ rows are current -> first row a[V=0][:]

    input-LUT[12][12] depending on array[inp_voltage][log(inp_current)],
    influence of cap-voltage is not implemented
    """

    LUT_input_V_min_log2_uV: Annotated[int, Field(ge=0, le=20)] = 0
    """ ⤷ i.e. 2^7 = 128 uV -> LUT[0][:] is for inputs < 128 uV"""
    LUT_input_I_min_log2_nA: Annotated[int, Field(ge=1, le=20)] = 1
    """ ⤷ i.e. 2^8 = 256 nA -> LUT[:][0] is for inputs < 256 nA"""

    # Buck Converter
    V_output_mV: Annotated[float, Field(ge=0, le=5_000)] = 2_400
    """ Fixed Voltage of Buck-Converter.
    (as long as Input is > Output + Drop-Voltage)
    """
    V_buck_drop_mV: Annotated[float, Field(ge=0, le=5_000)] = 0
    """ ⤷ simulate LDO / diode minimum voltage differential or output-diode"""

    LUT_output_efficiency: LUT1D = 12 * [1.00]
    """ ⤷ array[12] depending on output_current, In- & Output is linear."""
    LUT_output_I_min_log2_nA: Annotated[int, Field(ge=1, le=20)] = 1
    """ ⤷ i.e. 2^8 = 256 nA -> LUT[0] is for inputs < 256 nA,
    see notes on LUT_input for explanation
    """

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        values, chain = tb_client.try_completing_model(cls.__name__, values)
        values = tb_client.fill_in_user_data(values)
        log.debug("VSrc-Inheritances: %s", chain)
        # TODO: most "internal states" should be corrected here

        return values

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        # trigger stricter test of harv-parameters
        HarvesterPRUConfig.from_vhrv(self.harvester, for_emu=True)
        # TODO: enable threshold < mid_max
        # TODO: mid_max < mid_soc1
        return self

    def calc_internal_states(self) -> dict:
        """Update the model-states for the capacitor and other elements.

        This also compensates for current-surge of real capacitors
        when the converter gets turned on:

        - surges are hard to detect & record
        - this can be const value, because
        - the converter always turns on with "V_storage_enable_threshold_uV".

        TODO: currently neglecting delay after disabling converter, boost
        only has simpler formula, second enabling when V_Cap >= V_out

        Math behind this calculation:

        - Energy-Change Storage Cap ->  E_new = E_old - E_output
        - with Energy of a Cap 	    -> 	E_x = C_x * V_x^2 / 2
        - combine formulas 		    ->  C_store * V_store_new^2 / 2 =
          C_store * V_store_old^2 / 2 - C_out * V_out^2 / 2
        - convert formula to V_new 	->	V_store_new^2 =
          V_store_old^2 - (C_out / C_store) * V_out^2
        - convert into dV	 	        ->	dV = V_store_new - V_store_old
        - in case of V_cap = V_out 	-> 	dV = V_store_old * (sqrt(1 - C_out / C_store) - 1)

        Note: dV values will be reversed (negated), because dV is always negative (Voltage drop)
        """
        values = {}
        if (self.storage is not None) and self.C_output_uF > 0:
            # first case: storage cap outside of en/dis-thresholds
            v_old = self.V_intermediate_enable_output_threshold_mV
            v_out = self.V_output_mV
            c_store = self.storage.capacity_in_uF
            c_out = self.C_output_uF
            dV_output_en_thrs_mV = v_old - pow(
                pow(v_old, 2) - (c_out / c_store) * pow(v_out, 2),
                0.5,
            )

            # second case: storage cap below v_out (only different for enabled buck),
            #              enable when >= v_out
            # v_enable is either bucks v_out or same dV-Value is calculated a second time
            dV_output_imed_low_mV = v_out * (1 - pow(1 - c_out / c_store, 0.5))
        else:
            dV_output_en_thrs_mV = 0
            dV_output_imed_low_mV = 0

        if self.enable_boost and self.storage is not None:
            # TODO: storage could have maximum at a different SoC, is this needed at all?
            values["V_mid_max_mV"] = min(
                self.V_intermediate_max_mV,
                1e3 * self.storage.calc_V_OC(SoC=1.0),
                10_000,
            )
        else:
            values["V_mid_max_mV"] = self.V_intermediate_max_mV

        # protect from complex solutions (non valid input combinations)
        if not (isinstance(dV_output_en_thrs_mV, (int, float)) and (dV_output_en_thrs_mV >= 0)):
            dV_output_en_thrs_mV = 0
        if not (isinstance(dV_output_imed_low_mV, (int, float)) and (dV_output_imed_low_mV >= 0)):
            log.warning("VSrc: C_output shouldn't be larger than C_intermediate")
            dV_output_imed_low_mV = 0

        # decide which hysteresis-thresholds to use for buck-converter
        if self.enable_buck > 0:
            V_pre_output_mV = self.V_output_mV + self.V_buck_drop_mV

            if self.V_intermediate_enable_output_threshold_mV > V_pre_output_mV:
                values["dV_mid_enable_output_mV"] = dV_output_en_thrs_mV
                values["V_mid_enable_output_threshold_mV"] = (
                    self.V_intermediate_enable_output_threshold_mV
                )

            else:
                values["dV_mid_enable_output_mV"] = dV_output_imed_low_mV
                values["V_mid_enable_output_threshold_mV"] = (
                    V_pre_output_mV + values["dV_mid_enable_output_mV"]
                )

            if self.V_intermediate_disable_output_threshold_mV > V_pre_output_mV:
                values["V_mid_disable_output_threshold_mV"] = (
                    self.V_intermediate_disable_output_threshold_mV
                )
            else:
                values["V_mid_disable_output_threshold_mV"] = V_pre_output_mV

        else:
            values["dV_mid_enable_output_mV"] = dV_output_en_thrs_mV
            values["V_mid_enable_output_threshold_mV"] = (
                self.V_intermediate_enable_output_threshold_mV
            )
            values["V_mid_disable_output_threshold_mV"] = (
                self.V_intermediate_disable_output_threshold_mV
            )
        return values

    def calc_converter_mode(self, dtype_in: EnergyDType, *, log_intermediate_node: bool) -> int:
        """Assembles bitmask from discrete values.

        log_intermediate_node: record / log virtual intermediate (cap-)voltage and
        -current (out) instead of output-voltage and -current
        """
        enable_storage = self.storage is not None
        enable_boost = self.enable_boost and enable_storage
        if enable_boost != self.enable_boost:
            log.warning("VSrc - boost was disabled due to missing storage capacitor!")
        enable_feedback = (
            self.enable_feedback_to_hrv
            and enable_storage
            and not enable_boost
            and dtype_in == EnergyDType.ivcurve
        )
        if enable_feedback != self.enable_feedback_to_hrv:
            reason = "enabled boost, " if enable_boost else ""
            reason += "" if dtype_in == EnergyDType.ivcurve else "input not ivcurve, "
            reason += "" if enable_storage else "no storage capacitor"
            log.warning("VSRC - feedback to harvester was disabled! Reasons: %s", reason)
        return (
            1 * int(enable_storage)
            + 2 * int(enable_boost)
            + 4 * int(self.enable_buck)
            + 8 * int(log_intermediate_node)
            + 16 * int(enable_feedback)
        )


u32 = Annotated[int, Field(ge=0, lt=2**32)]
u8 = Annotated[int, Field(ge=0, lt=2**8)]
lut_i = Annotated[
    list[Annotated[list[u8], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]],
    Field(
        min_length=LUT_SIZE,
        max_length=LUT_SIZE,
    ),
]
lut_o = Annotated[list[u32], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]


class ConverterPRUConfig(ShpModel):
    """Map settings-list to internal state-vars struct ConverterConfig.

    NOTE:
      - yaml is based on si-units like nA, mV, ms, uF
      - c-code and py-copy is using nA, uV, ns, nF, fW, raw
      - ordering is intentional and in sync with shepherd/commons.h
    """

    converter_mode: u32
    interval_startup_delay_drain_n: u32

    V_input_max_uV: u32
    I_input_max_nA: u32
    V_input_drop_uV: u32
    R_input_kOhm_n22: u32
    # ⤷ TODO: possible optimization: n32 (range 1uOhm to 1 kOhm) is easier to calc in pru

    V_mid_enable_output_threshold_uV: u32
    V_mid_disable_output_threshold_uV: u32
    dV_mid_enable_output_uV: u32
    interval_check_thresholds_n: u32

    V_pwr_good_enable_threshold_uV: u32
    V_pwr_good_disable_threshold_uV: u32
    immediate_pwr_good_signal: u32

    V_output_log_gpio_threshold_uV: u32

    V_input_boost_threshold_uV: u32
    V_mid_max_uV: u32

    V_output_uV: u32
    V_buck_drop_uV: u32

    LUT_input_V_min_log2_uV: u32
    LUT_input_I_min_log2_nA: u32
    LUT_output_I_min_log2_nA: u32
    LUT_inp_efficiency_n8: lut_i
    LUT_out_inv_efficiency_n4: lut_o

    @classmethod
    def from_vsrc(
        cls,
        data: VirtualSourceConfig,
        dtype_in: EnergyDType = EnergyDType.ivsample,
        *,
        log_intermediate_node: bool = False,
    ) -> Self:
        states = data.calc_internal_states()
        return cls(
            # General
            converter_mode=data.calc_converter_mode(
                dtype_in, log_intermediate_node=log_intermediate_node
            ),
            interval_startup_delay_drain_n=round(
                data.interval_startup_delay_drain_ms * config.SAMPLERATE_SPS * 1e-3
            ),
            V_input_max_uV=round(data.V_input_max_mV * 1e3),
            I_input_max_nA=round(data.I_input_max_mA * 1e6),
            V_input_drop_uV=round(data.V_input_drop_mV * 1e3),
            R_input_kOhm_n22=round(data.R_input_mOhm * (1e-6 * 2**22)),
            V_mid_enable_output_threshold_uV=round(
                states["V_mid_enable_output_threshold_mV"] * 1e3
            ),
            V_mid_disable_output_threshold_uV=round(
                states["V_mid_disable_output_threshold_mV"] * 1e3
            ),
            dV_mid_enable_output_uV=round(states["dV_mid_enable_output_mV"] * 1e3),
            interval_check_thresholds_n=round(
                data.interval_check_thresholds_ms * config.SAMPLERATE_SPS * 1e-3
            ),
            V_pwr_good_enable_threshold_uV=round(data.V_pwr_good_enable_threshold_mV * 1e3),
            V_pwr_good_disable_threshold_uV=round(data.V_pwr_good_disable_threshold_mV * 1e3),
            immediate_pwr_good_signal=data.immediate_pwr_good_signal,
            V_output_log_gpio_threshold_uV=round(data.V_output_log_gpio_threshold_mV * 1e3),
            # Boost-Converter
            V_input_boost_threshold_uV=round(data.V_input_boost_threshold_mV * 1e3),
            V_mid_max_uV=round(states["V_mid_max_mV"] * 1e3),
            # Buck-Converter
            V_output_uV=round(data.V_output_mV * 1e3),
            V_buck_drop_uV=round(data.V_buck_drop_mV * 1e3),
            # LUTs
            LUT_input_V_min_log2_uV=data.LUT_input_V_min_log2_uV,
            LUT_input_I_min_log2_nA=data.LUT_input_I_min_log2_nA - 1,  # sub-1 due to later log2-op
            LUT_output_I_min_log2_nA=data.LUT_output_I_min_log2_nA - 1,  # sub-1 due to later log2
            LUT_inp_efficiency_n8=[
                [min(255, round(256 * ival)) for ival in il] for il in data.LUT_input_efficiency
            ],
            LUT_out_inv_efficiency_n4=[
                min((2**14), round((2**4) / value)) if (value > 0) else (2**14)
                for value in data.LUT_output_efficiency
            ],
        )

    def storage_is_enabled(self) -> bool:
        return bool(self.converter_mode & 1)

    def boost_is_enabled(self) -> bool:
        return bool(self.converter_mode & 2)

    def buck_is_enabled(self) -> bool:
        return bool(self.converter_mode & 4)

    def logging_intermediate_node_is_enabled(self) -> bool:
        return bool(self.converter_mode & 8)

    def feedback_is_enabled(self) -> bool:
        return bool(self.converter_mode & 16)
