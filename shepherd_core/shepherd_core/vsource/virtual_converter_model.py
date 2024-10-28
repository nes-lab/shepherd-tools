"""This is ported py-version of the pru-code.

Goals:

- stay close to original code-base
- offer a comparison for the tests
- step 1 to a virtualization of emulation

NOTE: DO NOT OPTIMIZE -> stay close to original code-base

Compromises:

- bitshifted values (i.e. _n28) are converted to float without shift

"""

import math
from typing import Optional

from ..data_models import CalibrationEmulator
from ..data_models.content.virtual_source import LUT_SIZE
from ..data_models.content.virtual_source import ConverterPRUConfig


class PruCalibration:
    """part of calibration.h."""

    # negative residue compensation - compensate for noise around 0
    # -> current uint-design cuts away negative part and leads to biased mean()
    NOISE_ESTIMATE_nA: int = 2000
    RESIDUE_SIZE_FACTOR: int = 30
    RESIDUE_MAX_nA: int = NOISE_ESTIMATE_nA * RESIDUE_SIZE_FACTOR
    negative_residue_nA = 0

    def __init__(self, cal_emu: Optional[CalibrationEmulator] = None) -> None:
        self.cal = cal_emu if cal_emu else CalibrationEmulator()

    def conv_adc_raw_to_nA(self, current_raw: int) -> float:
        I_nA = self.cal.adc_C_A.raw_to_si(current_raw) * (10**9)
        if self.cal.adc_C_A.offset < 0:
            if I_nA > self.negative_residue_nA:
                I_nA -= self.negative_residue_nA
                self.negative_residue_nA = 0
            else:
                self.negative_residue_nA = self.negative_residue_nA - I_nA
                self.negative_residue_nA = min(self.negative_residue_nA, self.RESIDUE_MAX_nA)
                I_nA = 0
        return I_nA

    @staticmethod
    def conv_adc_raw_to_uV(voltage_raw: int) -> None:
        msg = f"This Fn should not been used (val={voltage_raw})"
        raise RuntimeError(msg)

    def conv_uV_to_dac_raw(self, voltage_uV: float) -> int:
        dac_raw = self.cal.dac_V_A.si_to_raw(float(voltage_uV) / (10**6))
        return min(dac_raw, (2**16) - 1)


class VirtualConverterModel:
    """Ported python version of the pru vCnv."""

    def __init__(self, cfg: ConverterPRUConfig, cal: PruCalibration) -> None:
        self._cal: PruCalibration = cal
        self._cfg: ConverterPRUConfig = cfg

        # simplifications for python
        self.R_input_kOhm = float(self._cfg.R_input_kOhm_n22) / 2**22
        self.Constant_us_per_nF = float(self._cfg.Constant_us_per_nF_n28) / 2**28

        # boost internal state
        self.V_input_uV: float = 0.0
        self.P_inp_fW: float = 0.0
        self.P_out_fW: float = 0.0
        self.interval_startup_disabled_drain_n: int = self._cfg.interval_startup_delay_drain_n

        # container for the stored energy
        self.V_mid_uV: float = self._cfg.V_intermediate_init_uV

        # buck internal state
        self.enable_storage: bool = (int(self._cfg.converter_mode) & 0b0001) > 0
        self.enable_boost: bool = (int(self._cfg.converter_mode) & 0b0010) > 0
        self.enable_buck: bool = (int(self._cfg.converter_mode) & 0b0100) > 0
        self.enable_log_mid: bool = (int(self._cfg.converter_mode) & 0b1000) > 0
        # back-channel to hrv
        self.feedback_to_hrv: bool = (int(self._cfg.converter_mode) & 0b1_0000) > 0
        self.V_input_request_uV: int = self._cfg.V_intermediate_init_uV

        self.V_out_dac_uV: float = self._cfg.V_output_uV
        self.V_out_dac_raw: int = self._cal.conv_uV_to_dac_raw(self._cfg.V_output_uV)
        self.power_good: bool = True

        # prepare hysteresis-thresholds
        self.dV_enable_output_uV: float = self._cfg.dV_enable_output_uV
        self.V_enable_output_threshold_uV: float = self._cfg.V_enable_output_threshold_uV
        self.V_disable_output_threshold_uV: float = self._cfg.V_disable_output_threshold_uV

        self.V_enable_output_threshold_uV = max(
            self.dV_enable_output_uV, self.V_enable_output_threshold_uV
        )

        # pulled from update_states_and_output() due to easier static init
        self.sample_count: int = 0xFFFFFFF0
        self.is_outputting: bool = False
        self.vsource_skip_gpio_logging: bool = False

    def calc_inp_power(self, input_voltage_uV: float, input_current_nA: float) -> int:
        # Next 2 lines are Python-specific (model unsigned int)
        input_voltage_uV = max(0.0, input_voltage_uV)
        input_current_nA = max(0.0, input_current_nA)

        # Input diode
        if input_voltage_uV > self._cfg.V_input_drop_uV:
            input_voltage_uV -= self._cfg.V_input_drop_uV
        else:
            input_voltage_uV = 0.0

        input_voltage_uV = min(input_voltage_uV, self._cfg.V_input_max_uV)

        input_current_nA = min(input_current_nA, self._cfg.I_input_max_nA)

        self.V_input_uV = input_voltage_uV

        if self.enable_boost:
            if input_voltage_uV < self._cfg.V_input_boost_threshold_uV:
                input_voltage_uV = 0.0
            # TODO: vdrop in case of v_input > v_storage (non-boost)
        elif self.enable_storage:
            # no boost, but cap, for ie. diode+cap (+resistor)
            V_diff_uV = (
                (input_voltage_uV - self.V_mid_uV) if (input_voltage_uV >= self.V_mid_uV) else 0
            )
            V_res_drop_uV = input_current_nA * self.R_input_kOhm
            if V_res_drop_uV > V_diff_uV:
                input_voltage_uV = self.V_mid_uV
            else:
                input_voltage_uV -= V_res_drop_uV

            # IF input==ivcurve request new CV
            if self.feedback_to_hrv:
                self.V_input_request_uV = self.V_mid_uV + V_res_drop_uV + self._cfg.V_input_drop_uV
            elif input_voltage_uV < self.V_mid_uV:
                # without feedback there is no usable energy here
                input_voltage_uV = 0
        else:
            # direct connection
            # modifying V_mid here is not clean, but simpler
            # -> V_mid is needed in calc_out, before cap is updated
            self.V_mid_uV = input_voltage_uV
            input_voltage_uV = 0.0
            # ⤷ input will not be evaluated

        if self.enable_boost:
            eta_inp = self.get_input_efficiency(input_voltage_uV, input_current_nA)
        else:
            eta_inp = 1.0

        self.P_inp_fW = eta_inp * input_voltage_uV * input_current_nA
        return round(self.P_inp_fW)  # Python-specific, added for easier testing

    def calc_out_power(self, current_adc_raw: int) -> int:
        # Next 2 lines are Python-specific (model unsigned int)
        current_adc_raw = max(0, current_adc_raw)
        current_adc_raw = min((2**18) - 1, current_adc_raw)

        P_leak_fW = self.V_mid_uV * self._cfg.I_intermediate_leak_nA
        I_out_nA = self._cal.conv_adc_raw_to_nA(current_adc_raw)
        if self.enable_buck:  # noqa: SIM108
            eta_inv_out = self.get_output_inv_efficiency(I_out_nA)
        else:
            eta_inv_out = 1.0

        self.P_out_fW = eta_inv_out * self.V_out_dac_uV * I_out_nA + P_leak_fW

        if self.interval_startup_disabled_drain_n > 0:
            self.interval_startup_disabled_drain_n -= 1
            self.P_out_fW = 0.0

        return round(self.P_out_fW)  # Python-specific, added for easier testing

    # TODO: add range-checks for add, sub Ops
    def update_cap_storage(self) -> int:
        # TODO: this calculation is wrong for everything beside boost-cnv
        if self.enable_storage:
            V_mid_prot_uV = max(1.0, self.V_mid_uV)
            P_sum_fW = self.P_inp_fW - self.P_out_fW
            I_mid_nA = P_sum_fW / V_mid_prot_uV
            dV_mid_uV = I_mid_nA * self.Constant_us_per_nF
            self.V_mid_uV += dV_mid_uV

        self.V_mid_uV = min(self.V_mid_uV, self._cfg.V_intermediate_max_uV)
        self.V_mid_uV = max(self.V_mid_uV, 1)
        return round(self.V_mid_uV)  # Python-specific, added for easier testing

    def update_states_and_output(self) -> int:
        self.sample_count += 1
        check_thresholds = self.sample_count >= self._cfg.interval_check_thresholds_n
        V_mid_uV_now = self.V_mid_uV
        # copy avoids not enabling pwr_good (due to large dV_enable_output_uV)

        if check_thresholds:
            self.sample_count = 0
            if self.is_outputting:
                if V_mid_uV_now < self.V_disable_output_threshold_uV:
                    self.is_outputting = False
            elif V_mid_uV_now >= self.V_enable_output_threshold_uV:
                self.is_outputting = True
                self.V_mid_uV -= self.dV_enable_output_uV

        if check_thresholds or self._cfg.immediate_pwr_good_signal:
            # generate power-good-signal
            if self.power_good:
                if V_mid_uV_now <= self._cfg.V_pwr_good_disable_threshold_uV:
                    self.power_good = False
            elif V_mid_uV_now >= self._cfg.V_pwr_good_enable_threshold_uV:
                self.power_good = self.is_outputting
            # set batok pin to state ... TODO?

        if self.is_outputting or self.interval_startup_disabled_drain_n > 0:
            if (not self.enable_buck) or (
                self.V_mid_uV <= self._cfg.V_output_uV + self._cfg.V_buck_drop_uV
            ):
                if self.V_mid_uV > self._cfg.V_buck_drop_uV:
                    self.V_out_dac_uV = self.V_mid_uV - self._cfg.V_buck_drop_uV
                else:
                    self.V_out_dac_uV = 0.0
            else:
                self.V_out_dac_uV = self._cfg.V_output_uV
            self.V_out_dac_raw = self._cal.conv_uV_to_dac_raw(self.V_out_dac_uV)
        else:
            self.V_out_dac_uV = 0.0
            self.V_out_dac_raw = 0

        self.vsource_skip_gpio_logging = (
            self.V_out_dac_uV < self._cfg.V_output_log_gpio_threshold_uV
        )
        return self.V_out_dac_raw

    def get_input_efficiency(self, voltage_uV: float, current_nA: float) -> float:
        voltage_n = int(voltage_uV / (2**self._cfg.LUT_input_V_min_log2_uV))
        current_n = int(current_nA / (2**self._cfg.LUT_input_I_min_log2_nA))
        pos_v = int(voltage_n) if (voltage_n > 0) else 0  # V-Scale is Linear!
        pos_c = int(math.log2(current_n)) if (current_n > 0) else 0
        if pos_v >= LUT_SIZE:
            pos_v = LUT_SIZE - 1
        if pos_c >= LUT_SIZE:
            pos_c = LUT_SIZE - 1
        return self._cfg.LUT_inp_efficiency_n8[pos_v][pos_c] / (2**8)

    def get_output_inv_efficiency(self, current_nA: float) -> float:
        current_n = int(current_nA / (2**self._cfg.LUT_output_I_min_log2_nA))
        pos_c = int(math.log2(current_n)) if (current_n > 0) else 0
        if pos_c >= LUT_SIZE:
            pos_c = LUT_SIZE - 1
        return self._cfg.LUT_out_inv_efficiency_n4[pos_c] / (2**4)

    def set_P_input_fW(self, value: float) -> None:
        self.P_inp_fW = value

    def set_P_output_fW(self, value: float) -> None:
        self.P_out_fW = value

    def set_V_intermediate_uV(self, value: float) -> None:
        self.V_mid_uV = value

    def get_P_input_fW(self) -> int:
        return round(self.P_inp_fW)

    def get_P_output_fW(self) -> int:
        return round(self.P_out_fW)

    def get_V_intermediate_uV(self) -> int:
        return round(self.V_mid_uV)

    def get_V_intermediate_raw(self) -> int:
        return round(self._cal.conv_uV_to_dac_raw(self.V_mid_uV))

    def get_power_good(self) -> bool:
        return self.power_good

    def get_I_mid_out_nA(self) -> float:
        return self.P_out_fW / self.V_mid_uV

    def get_state_log_intermediate(self) -> bool:
        return self.enable_log_mid

    def get_state_log_gpio(self) -> bool:
        return self.vsource_skip_gpio_logging
