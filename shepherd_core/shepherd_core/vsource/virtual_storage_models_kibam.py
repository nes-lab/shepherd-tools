"""Original KiBaM-Models with varying quality of detail."""

import math
import sys
from collections.abc import Callable
from typing import Self

from pydantic import BaseModel
from pydantic import PositiveFloat
from pydantic import PositiveInt
from pydantic import validate_call

from shepherd_core.data_models.content.virtual_storage_config import LuT_SIZE
from shepherd_core.data_models.content.virtual_storage_config import TIMESTEP_s_DEFAULT
from shepherd_core.data_models.content.virtual_storage_config import VirtualStorageConfig
from shepherd_core.data_models.content.virtual_storage_config import soc_t

from .virtual_storage_model import ModelStorage


class LUT(BaseModel):
    """Dynamic look-up table that can automatically be generated from a function."""

    x_min: float
    y_values: list[float]
    length: int
    interpolate: bool = False

    @classmethod
    @validate_call
    def generate(
        cls,
        x_min: PositiveFloat,
        y_fn: Callable,
        lut_size: PositiveInt = LuT_SIZE,
        *,
        optimize_clamp: bool = False,
        interpolate: bool = False,
    ) -> Self:
        """
        Generate a LUT with a specific width from a provided function.

        It has a minimum value, a size / width and a scale (linear / log2).
        y_fnc is a function that takes an argument and produces the lookup value.
        """
        if interpolate:
            # Note: dynamically creating .get() with setattr() was not successful
            optimize_clamp = False

        offset = 0.5 if optimize_clamp else 0
        x_values = [(i + offset) * x_min for i in range(lut_size)]
        y_values = [y_fn(x) for x in x_values]
        return cls(x_min=x_min, y_values=y_values, length=lut_size, interpolate=interpolate)

    def get(self, x_value: float) -> float:
        return self.get_interpol(x_value) if self.interpolate else self.get_discrete(x_value)

    def get_discrete(self, x_value: float) -> float:
        """Discrete LuT-lookup with typical stairs."""
        num = int(x_value / self.x_min)
        # ⤷ round() would be more appropriate, but in c/pru its just integer math
        idx = max(0, num)
        if idx >= self.length:  # len(self.y_values)
            idx = self.length - 1
        return self.y_values[idx]

    def get_interpol(self, x_value: float) -> float:
        """LuT-lookup with additional interpolation.

        Note: optimize-clamp must be disabled, otherwise this produces an offset
        """
        num = x_value / self.x_min
        if num <= 0:
            return self.y_values[0]
        if num >= self.length - 1:
            return self.y_values[self.length - 1]

        idx: int = math.floor(num)
        # high could be math.ceil(num), but also idx+1
        num_f: float = num - idx
        y_base = self.y_values[idx]
        y_delta = self.y_values[idx + 1] - y_base
        # TODO: y_delta[idx_l] could be a seconds LuT
        return y_base + y_delta * num_f


class ModelKiBaM(ModelStorage):
    """Naive implementation of the full hybrid KiBaM model from the paper.

    Introduced in "A Hybrid Battery Model Capable of Capturing Dynamic Circuit
    Characteristics and Nonlinear Capacity Effects".

    It is mostly focused on discharge, so it won't support

    - rate capacity effect and transients during charging
    - self discharge (as it was deemed too small)
    """

    @validate_call
    def __init__(
        self,
        cfg: VirtualStorageConfig,
        SoC_init: soc_t | None = None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
    ) -> None:
        # metadata for simulator
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC_init if SoC_init is not None else cfg.SoC_init
        self.time_s: float = 0

        # Rate capacity effect
        self.C_unavailable: float = 0
        self.C_unavailable_last: float = 0

        # Transient tracking
        self.V_transient_S_max: float = 0
        self.V_transient_L_max: float = 0
        self.discharge_last: bool = False

        # Modified transient tracking
        self.V_transient_S: float = 0
        self.V_transient_L: float = 0

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        # Step 1 verified separately using Figure 4
        # Steps 1 and 2 verified separately using Figure 10
        # Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)
        I_cell = -I_charge_A

        # Step 0: Determine whether battery is charging or resting and
        #         calculate time since last switch
        if self.discharge_last != (I_cell > 0):  # Reset time delta when current sign changes
            self.discharge_last = I_cell > 0
            self.time_s = 0
            self.C_unavailable_last = self.C_unavailable
            # ⤷ Save C_unavailable at time of switch

        self.time_s += self.dt_s
        # ⤷ Consider time delta including this iteration (we want v_trans after the current step)

        # Step 1: Calculate unavailable capacity after dt
        #         (due to rate capacity and recovery effect) (equation 17)
        # Note: it seems possible to remove the 2nd branch if
        #       charging is considered (see Plus-Model)
        if I_cell > 0:  # Discharging
            self.C_unavailable = (
                self.C_unavailable_last * math.pow(math.e, -self.cfg.kdash * self.time_s)
                + (1 - self.cfg.p_rce)
                * I_cell
                / self.cfg.p_rce
                * (1 - math.pow(math.e, -self.cfg.kdash * self.time_s))
                / self.cfg.kdash
            )
        else:  # Recovering
            self.C_unavailable = self.C_unavailable_last * math.pow(
                math.e, -self.cfg.kdash * self.time_s
            )

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        # ⤷ MODIFIED: clamp both SoC to 0..1
        self.SoC = self.SoC - 1 / self.cfg.q_As * (I_cell * self.dt_s)
        self.SoC = min(max(self.SoC, 0.0), 1.0)
        SoC_eff = self.SoC - 1 / self.cfg.q_As * self.C_unavailable
        SoC_eff = max(SoC_eff, 0.0)

        # Step 3: Calculate V_OC after dt (equation 7)
        V_OC = self.cfg.calc_V_OC(SoC_eff)

        # Step 4: Calculate resistance and capacitance values after dt (equation 12)
        R_series = self.cfg.calc_R_series(SoC_eff)
        R_transient_S = self.cfg.calc_R_transient_S(SoC_eff)
        C_transient_S = self.cfg.calc_C_transient_S(SoC_eff)
        R_transient_L = self.cfg.calc_R_transient_L(SoC_eff)
        C_transient_L = self.cfg.calc_C_transient_L(SoC_eff)

        # Step 5: Calculate transient voltages (equations 10 and 11)
        # ⤷ MODIFIED: prevent both tau_X from becoming 0
        tau_S = max(R_transient_S * C_transient_S, sys.float_info.min)
        if I_cell > 0:  # Discharging
            V_transient_S = R_transient_S * I_cell * (1 - math.pow(math.e, -self.time_s / tau_S))
            self.V_transient_S_max = V_transient_S
        else:  # Recovering
            V_transient_S = self.V_transient_S_max * math.pow(math.e, -self.time_s / tau_S)

        tau_L = max(R_transient_L * C_transient_L, sys.float_info.min)
        if I_cell > 0:  # Discharging
            V_transient_L = R_transient_L * I_cell * (1 - math.pow(math.e, -self.time_s / tau_L))
            self.V_transient_L_max = V_transient_L
        else:  # Recovering
            V_transient_L = self.V_transient_L_max * math.pow(math.e, -self.time_s / tau_L)

        # Step 6: Calculate cell voltage (equations 8 and 9)
        # ⤷ MODIFIED: limit V_cell to >=0
        V_transient = V_transient_S + V_transient_L
        V_cell = V_OC - I_cell * R_series - V_transient
        V_cell = max(V_cell, 0)

        return V_OC, V_cell, self.SoC, SoC_eff


class ModelKiBaMPlus(ModelStorage):
    """Hybrid KiBaM model from the paper with certain extensions.

    Extended by [@jonkub](https://github.com/jonkub) with streamlined math.

    Modifications:

    1. support rate capacity during charging (Step 1)
    2. support transient tracking during charging (Step 5)
    3. support self discharge (step 2a) via a parallel leakage resistor
    """

    @validate_call
    def __init__(
        self,
        cfg: VirtualStorageConfig,
        SoC_init: soc_t | None = None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
    ) -> None:
        # metadata for simulator
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC_init if SoC_init is not None else cfg.SoC_init
        self.time_s: float = 0

        # Rate capacity effect
        self.C_unavailable: float = 0
        self.C_unavailable_last: float = 0

        # Transient tracking
        self.discharge_last: bool = False

        # Modified transient tracking
        self.V_transient_S: float = 0
        self.V_transient_L: float = 0

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step.

        - Step 1 verified separately using Figure 4
        - Steps 1 and 2 verified separately using Figure 10
        - Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)
        """
        I_cell = -I_charge_A

        # Step 0: Determine whether battery is charging or resting and
        #         calculate time since last switch
        if self.discharge_last != (I_cell > 0):  # Reset time delta when current sign changes
            self.discharge_last = I_cell > 0
            self.time_s = 0
            self.C_unavailable_last = self.C_unavailable  # Save C_unavailable at time of switch

        self.time_s += self.dt_s
        # ⤷ Consider time delta including this iteration (we want v_trans after the current step)

        # Step 1: Calculate unavailable capacity after dt
        #         (due to rate capacity and recovery effect) (equation 17)
        # TODO: if this should be used in production, additional verification is required
        #      (analytically derive versions of eq. 16/17 without time range restrictions)
        #       parameters for rate effect could only be valid for discharge
        #       Note: other paper has charging-curves (fig9b) - could be used for verification
        self.C_unavailable = (
            self.C_unavailable_last * math.pow(math.e, -self.cfg.kdash * self.time_s)
            + (1 - self.cfg.p_rce)
            * I_cell
            / self.cfg.p_rce
            * (1 - math.pow(math.e, -self.cfg.kdash * self.time_s))
            / self.cfg.kdash
        )

        # Step 2a: Calculate and add self-discharge current to SoC-Eq. below
        I_leak = self.cfg.calc_V_OC(self.SoC) / self.cfg.R_leak_Ohm

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        # ⤷ MODIFIED: clamp both SoC to 0..1
        self.SoC = self.SoC - (I_cell + I_leak) * self.dt_s / self.cfg.q_As
        self.SoC = min(max(self.SoC, 0.0), 1.0)
        SoC_eff = self.SoC - 1 / self.cfg.q_As * self.C_unavailable
        SoC_eff = min(max(SoC_eff, 0.0), 1.0)
        # ⤷ Note: limiting SoC_eff to <=1 should NOT be needed, but
        #         C_unavailable can become negative during charging (see assumption in step1).

        # Step 3: Calculate V_OC after dt (equation 7)
        V_OC = self.cfg.calc_V_OC(SoC_eff)

        # Step 4: Calculate resistance and capacitance values after dt (equation 12)
        R_series = self.cfg.calc_R_series(SoC_eff)
        R_transient_S = self.cfg.calc_R_transient_S(SoC_eff)
        C_transient_S = self.cfg.calc_C_transient_S(SoC_eff)
        R_transient_L = self.cfg.calc_R_transient_L(SoC_eff)
        C_transient_L = self.cfg.calc_C_transient_L(SoC_eff)

        # Step 5: Calculate transient voltages (equations 10 and 11)
        # ⤷ MODIFIED: prevent both tau_X from becoming 0
        tau_S = max(R_transient_S * C_transient_S, sys.float_info.min)
        tau_L = max(R_transient_L * C_transient_L, sys.float_info.min)
        self.V_transient_S = R_transient_S * I_cell + (
            self.V_transient_S - R_transient_S * I_cell
        ) * math.pow(math.e, -self.dt_s / tau_S)
        self.V_transient_L = R_transient_L * I_cell + (
            self.V_transient_L - R_transient_L * I_cell
        ) * math.pow(math.e, -self.dt_s / tau_L)

        # Step 6: Calculate cell voltage (equations 8 and 9)
        # ⤷ MODIFIED: limit V_cell to >=0
        V_transient = self.V_transient_S + self.V_transient_L
        V_cell = V_OC - I_cell * R_series - V_transient
        V_cell = max(V_cell, 0)

        return V_OC, V_cell, self.SoC, SoC_eff


class ModelKiBaMSimple(ModelStorage):
    """PRU-optimized model with a set of simplifications.

    Modifications by [@jonkub](https://github.com/jonkub):

    - omit transient voltages (step 4 & 5, expensive calculation)
    - omit rate capacity effect (step 1, expensive calculation)
    - replace two expensive Fn by LuT
        - mapping SoC to open circuit voltage (step 3)
        - mapping SoC to series resistance (step 4)
    - add self discharge resistance (step 2a)

    Compared to the current shepherd capacitor (charge-based), it:

    - supports emulation of battery types like lipo and lead acid (non-linear SOC-to-V_OC mapping)
    - has a parallel leakage resistor instead of an oversimplified leakage current
    - a series resistance is added to improve model matching
    - as a drawback the open circuit voltage is quantified and shows steps (LuT with 128 entries)

    """

    @validate_call
    def __init__(
        self,
        cfg: VirtualStorageConfig,
        SoC_init: soc_t | None = None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
        *,
        optimize_clamp: bool = False,
        interpolate: bool = False,
    ) -> None:
        # metadata for simulator
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s = dt_s
        # pre-calculate constants
        self.V_OC_LuT: LUT = LUT.generate(
            1.0 / LuT_SIZE,
            y_fn=cfg.calc_V_OC,
            lut_size=LuT_SIZE,
            optimize_clamp=optimize_clamp,
            interpolate=interpolate,
        )
        self.R_series_LuT: LUT = LUT.generate(
            1.0 / LuT_SIZE,
            y_fn=cfg.calc_R_series,
            lut_size=LuT_SIZE,
            optimize_clamp=optimize_clamp,
            interpolate=interpolate,
        )
        self.Constant_s_per_As: float = dt_s / cfg.q_As
        self.Constant_1_per_Ohm: float = 1.0 / cfg.R_leak_Ohm
        # state
        self.SoC: float = SoC_init if SoC_init is not None else cfg.SoC_init

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        I_cell = -I_charge_A
        # Step 2a: Calculate self-discharge (drainage)
        I_leak = self.V_OC_LuT.get(self.SoC) * self.Constant_1_per_Ohm

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        #       = SoC - 1 / C * (i_cell * dt)
        self.SoC = self.SoC - (I_cell + I_leak) * self.Constant_s_per_As
        SoC_eff = self.SoC = min(max(self.SoC, 0.0), 1.0)
        # ⤷ MODIFIED: removed term due to omission of rate capacity effect
        # ⤷ MODIFIED: clamp SoC to 0..1

        # Step 3: Calculate V_OC after dt (equation 7)
        # MODIFIED to use a lookup table instead
        V_OC = self.V_OC_LuT.get(SoC_eff)

        # Step 4: Calculate resistance and capacitance values after dt (equation 12)
        # MODIFIED: removed terms due to omission of transient voltages
        # MODIFIED to use a lookup table instead
        R_series = self.R_series_LuT.get(SoC_eff)

        # Step 5: Calculate transient voltages (equations 10 and 11)
        # MODIFIED: removed due to omission of transient voltages

        # Step 6: Calculate cell voltage (equations 8 and 9)
        # MODIFIED: removed term due to omission of transient voltages
        # MODIFIED: limit V_cell to >=0
        V_cell = V_OC - I_cell * R_series
        V_cell = max(V_cell, 0.0)

        return V_OC, V_cell, self.SoC, SoC_eff


class ModelShpCap(ModelStorage):
    """A derived model from shepherd-codebase for comparing to KiBaM-capacitor.

    This model was used for the intermediate storage capacitor until
    the battery-model was implemented.
    """

    @validate_call
    def __init__(
        self,
        cfg: VirtualStorageConfig,
        SoC_init: soc_t | None = None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
    ) -> None:
        # metadata for simulator
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s = dt_s
        # pre-calculate constants
        self.V_mid_max_V = cfg.calc_V_OC(1.0)
        C_mid_uF = 1e6 * cfg.q_As / self.V_mid_max_V
        C_mid_uF = max(C_mid_uF, 0.001)
        SAMPLERATE_SPS = 1.0 / dt_s
        self.Constant_s_per_F = 1e6 / (C_mid_uF * SAMPLERATE_SPS)
        self.Constant_1_per_Ohm: float = 1.0 / cfg.R_leak_Ohm
        # state
        SoC_init = SoC_init if SoC_init is not None else cfg.SoC_init
        self.V_mid_V = cfg.calc_V_OC(SoC_init)

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        # in PRU P_inp and P_out are calculated and combined to determine current
        # similar to: P_sum_W = P_inp_W - P_out_W, I_mid_A = P_sum_W / V_mid_V
        I_mid_A = I_charge_A - self.V_mid_V * self.Constant_1_per_Ohm
        dV_mid_V = I_mid_A * self.Constant_s_per_F
        self.V_mid_V += dV_mid_V

        self.V_mid_V = min(self.V_mid_V, self.V_mid_max_V)
        self.V_mid_V = max(self.V_mid_V, sys.float_info.min)
        SoC = self.V_mid_V / self.V_mid_max_V
        return self.V_mid_V, self.V_mid_V, SoC, SoC
