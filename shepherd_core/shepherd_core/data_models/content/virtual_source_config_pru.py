"""Generalized virtual source data models."""

from typing import Annotated
from typing import final

from pydantic import Field
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.shepherd import ShpModel

from .enum_datatypes import EnergyDType
from .virtual_source_config import LUT_SIZE
from .virtual_source_config import VirtualSourceConfig

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


@final
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
