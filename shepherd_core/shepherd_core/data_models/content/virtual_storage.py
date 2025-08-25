"""Generalized virtual energy storage data models (config)."""

import math
import sys
from collections.abc import Callable
from collections.abc import Sequence
from datetime import timedelta
from typing import Annotated
from typing import Any

from annotated_types import Ge
from annotated_types import Gt
from annotated_types import Le
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client


class VirtualStorageConfig(ContentModel, title="Config for the virtual energy storage"):
    """KiBaM Battery model based on two papers.

    Model An Accurate Electrical Battery Model Capable
        of Predicting Runtime and I-V Performance
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf

    A Hybrid Battery Model Capable of Capturing Dynamic Circuit
        Characteristics and Nonlinear Capacity Effects
    https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1210&context=electricalengineeringfacpub
    """

    # TODO: refine value-boundaries

    q_As: Annotated[float, Gt(0)]
    """ ⤷ Capacity (electrical charge) of Storage."""
    p_VOC: Annotated[Sequence[float], Field(min_length=6, max_length=6)] = [0, 0, 0, 1, 0, 0]
    """ ⤷ Parameters for V_OC-Mapping
        - direct SOC-Mapping by default
        - named a0 to a5 in paper
        """
    p_Rs: Annotated[Sequence[float], Field(min_length=6, max_length=6)] = [0, 0, 0, 0, 0, 0]
    """ ⤷ Parameters for series-resistance
        - no resistance set by default
        - named b0 to b5 in paper
        """
    p_RtS: Annotated[Sequence[float], Field(min_length=3, max_length=3)] = [0, 0, 0]
    """ ⤷ Parameters for R_transient_S (short-term),
        - no transient active by default
        - named c0 to c2 in paper
        """
    p_CtS: Annotated[Sequence[float], Field(min_length=3, max_length=3)] = [0, 0, 0]
    """ ⤷ Parameters for C_transient_S (short-term)
        - no transient active by default
        - named d0 to d2 in paper
        """
    p_RtL: Annotated[Sequence[float], Field(min_length=3, max_length=3)] = [0, 0, 0]
    """ ⤷ Parameters for R_transient_L (long-term)
        - no transient active by default
        - named e0 to e2 in paper
        """
    p_CtL: Annotated[Sequence[float], Field(min_length=3, max_length=3)] = [0, 0, 0]
    """ ⤷ Parameters for C_transient_L (long-term)
        - no transient active by default
        - named f0 to f2 in paper
        """

    p_rce: Annotated[float, Gt(0), Le(1.0)] = 1.0
    """ ⤷ Parameter for rate capacity effect
        - Set to 1 to disregard
        - named c in paper
        """
    kdash: Annotated[float, Gt(0)] = sys.float_info.min  # TODO: use k directly
    """ ⤷ Parameter for rate capacity effect
        - temporary component of rate capacity effect, valve in KiBaM (eq 17)
        - k' = k/c(1-c),
        """

    R_leak_Ohm: Annotated[float, Gt(0)] = sys.float_info.max
    """ ⤷ Parameter for self discharge (custom extension)
        - effect is often very small, mostly relevant for some capacitors
        """

    @classmethod
    @validate_call
    def lipo(cls, capacity_mAh: Annotated[float, Gt(0)]) -> Self:
        """Modeled after the PL-383562 2C Polymer Lithium-ion Battery.

        Nominal Voltage     3.7 V
        Nominal Capacity    860 mAh
        Discharge Cutoff    3.0 V
        Charge Cutoff       4.2 V
        Max Discharge       2 C / 1.72 A
        https://www.batteryspace.com/prod-specs/pl383562.pdf

        """
        return cls(
            q_As=capacity_mAh * 3600 / 1000,
            p_VOC=[-0.852, 63.867, 3.6297, 0.559, 0.51, 0.508],
            p_Rs=[0.1463, 30.27, 0.1037, 0.0584, 0.1747, 0.1288],
            p_RtS=[0.1063, 62.49, 0.0437],
            p_CtS=[-200, 138, 300],  # most likely a mistake (d1=-138) in the table/paper!
            p_RtL=[0.0712, 61.4, 0.0288],
            p_CtL=[-3083, 180, 5088],
            # y10 = 2863.3, y20 = 232.66 # unused
            p_rce=0.9248,
            kdash=0.0008,
            # content-fields below
            name=f"LiPo {capacity_mAh} mAh",
            description="Model of a standard LiPo battery (3 to 4.2 V) with adjustable capacity",
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @classmethod
    @validate_call
    def lead_acid(cls, capacity_mAh: Annotated[float, Gt(0)]) -> Self:
        """Modeled after the LEOCH LP12-1.2AH lead acid battery.

        Nominal Voltage     12 V
        Nominal Capacity    1.2 Ah
        Discharge Cutoff    10.8 V
        Charge Cutoff       13.5 V
        Max Discharge       15 C / 18 A
        https://www.leoch.com/pdf/reserve-power/agm-vrla/lp-general/LP12-1.2.pdf
        """
        return cls(
            q_As=capacity_mAh * 3600 / 1000,
            p_VOC=[5.429, 117.5, 11.32, 2.706, 2.04, 1.026],
            p_Rs=[1.578, 8.527, 0.7808, -1.887, -2.404, -0.649],
            p_RtS=[2.771, 9.079, 0.22],
            p_CtS=[-2423, 75.14, 55],
            p_RtL=[2.771, 9.079, 0.218],
            # ⤷ first 2 values of p_RtL are identical with p_RtS in table/paper
            #   (strange, but plots look fine)
            p_CtL=[-1240, 9.571, 3100],
            # y10 = 2592, y20 = 1728 # unused
            p_rce=0.6,
            kdash=0.0034,
            # content-fields below
            name=f"Lead-Acid-battery {capacity_mAh} mAh",
            description="Model of a 12V lead acid battery with adjustable capacity",
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @classmethod
    @validate_call
    def capacitor(
        cls,
        C_uF: Annotated[float, Gt(0)],
        V_rated: Annotated[float, Gt(0)],
        R_series_Ohm: Annotated[float, Ge(0)] = 0.0,
        R_self_Ohm: Annotated[float, Gt(0)] = sys.float_info.max,
    ) -> Self:
        return cls(
            q_As=1e-6 * C_uF * V_rated,
            p_VOC=[0, 0, 0, V_rated, 0, 0],  # 100% SoC is @V_rated,
            # no transients per default
            p_Rs=[0, 0, R_series_Ohm, 0, 0, 0],  # const series resistance
            R_leak_Ohm=R_self_Ohm,
            # content-fields below
            name=f"Capacitor {C_uF:.0f} uF",
            description="Model of a Capacitor with [DC-Bias], series & leakage resistor",
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        if False:  # TODO: create fixture first
            values, chain = tb_client.try_completing_model(cls.__name__, values)
            values = tb_client.fill_in_user_data(values)
            log.debug("vStorage-Inheritances: %s", chain)
        return values

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        return self

    def without_rate_capacity(self) -> Self:
        # ⤷ TODO: still needed?
        model_dict = self.model_dump()
        model_dict["p_rce"] = 1
        model_dict["name"] += " no_rate_cap"
        return type(self)(**model_dict)

    def without_transient_voltages(self) -> Self:
        # ⤷ TODO: still needed?
        # TODO: wouldn't it be more correct to set c0 to f2 to zero?
        model_dict = self.model_dump()
        model_dict["p_CtS"][2] = sys.float_info.max
        model_dict["p_CtL"][2] = sys.float_info.max
        model_dict["name"] += " no_transient_vs"
        return type(self)(**model_dict)

    def calc_R_self_discharge(
        self, duration: timedelta, SoC_final: float, SoC_0: float = 1.0
    ) -> float:
        # based on capacitor discharge: U(t) = U0 * e ^ (-t/RC)
        # Example: 50mAh; SoC from 100 % to 85 % over 30 days => ~1.8 MOhm
        U0 = self.calc_V_OC(SoC_0)
        Ut = self.calc_V_OC(SoC_final)
        return duration.total_seconds() * U0 / (self.q_As * math.log(U0 / Ut))

    def calc_V_OC(self, SoC: float) -> float:
        return (
            self.p_VOC[0] * math.pow(math.e, -self.p_VOC[1] * SoC)
            + self.p_VOC[2]
            + self.p_VOC[3] * SoC
            - self.p_VOC[4] * SoC**2
            + self.p_VOC[5] * SoC**3
        )

    def calc_R_series(self, SoC: float) -> float:
        return (
            self.p_Rs[0] * math.pow(math.e, -self.p_Rs[1] * SoC)
            + self.p_Rs[2]
            + self.p_Rs[3] * SoC
            - self.p_Rs[4] * SoC**2
            + self.p_Rs[5] * SoC**3
        )

    def calc_R_transient_S(self, SoC: float) -> float:
        return self.p_RtS[0] * math.pow(math.e, -self.p_RtS[1] * SoC) + self.p_RtS[2]

    def calc_C_transient_S(self, SoC: float) -> float:
        return self.p_CtS[0] * math.pow(math.e, -self.p_CtS[1] * SoC) + self.p_CtS[2]

    def calc_R_transient_L(self, SoC: float) -> float:
        return self.p_RtL[0] * math.pow(math.e, -self.p_RtL[1] * SoC) + self.p_RtL[2]

    def calc_C_transient_L(self, SoC: float) -> float:
        return self.p_CtL[0] * math.pow(math.e, -self.p_CtL[1] * SoC) + self.p_CtL[2]


# custom types
LUT_SIZE = 128
u32 = Annotated[int, Field(ge=0, lt=2**32)]
lut_storage = Annotated[list[u32], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]


class StoragePRUConfig(ShpModel):
    """Map settings-list to internal state-vars struct StorageConfig.

    NOTE:
      - yaml is based on si-units like nA, mV, ms, uF
      - c-code and py-copy is using nA, uV, ns, nF, fW, raw
      - ordering is intentional and in sync with shepherd/commons.h
    """

    Constant_s_per_mAs_n48: u32
    Constant_1_per_kOhm_n18: u32
    LuT_VOC_SoC_min_log2_1u_n32: u32
    # ⤷ TODO: why n32? c-code is strange (could be taken upper u32 of u64 and only shift that)
    #         guess u_n32 may be log2((2**32 * 1e6) * LuT_VOC_SoC_min) which is log2() + 32
    LuT_VOC_uV_n8: lut_storage
    """⤷ ranges from 3.9 uV to 16.7 V"""
    LuT_RSeries_SoC_min_log2_1u_n32: u32
    # ⤷ TODO: see above
    LuT_RSeries_kOhm_n32: lut_storage
    """⤷ ranges from 233n to 1 kOhm"""

    @classmethod
    def from_vstorage(cls, data: VirtualStorageConfig, *, optimize_clamp: bool = False) -> Self:
        x_off = 0.5 if optimize_clamp else 1.0
        LuT_VOC_SoC_min = 1.0 / LUT_SIZE
        V_OC_LuT = [data.calc_V_OC(LuT_VOC_SoC_min * (x + x_off)) for x in range(LUT_SIZE)]
        LuT_RSeries_SoC_min = 1.0 / LUT_SIZE
        R_series_LuT = [
            data.calc_R_series(LuT_RSeries_SoC_min * (x + x_off)) for x in range(LUT_SIZE)
        ]
        Constant_s_per_As: float = 10e-6 / data.q_As
        Constant_1_per_Ohm: float = 1.0 / data.R_leak_Ohm
        return cls(
            Constant_s_per_mAs_n48=int((2**48 / 1e3) * Constant_s_per_As),
            Constant_1_per_kOhm_n18=int((2**18 / 1e-3) * Constant_1_per_Ohm),
            LuT_VOC_SoC_min_log2_1u_n32=int(math.log2((2**32 * 1e6) * LuT_VOC_SoC_min)),
            LuT_VOC_uV_n8=[int((2**8 * 1e6) * y) for y in V_OC_LuT],
            LuT_RSeries_SoC_min_log2_1u_n32=int(math.log2((2**32 * 1e6) * LuT_RSeries_SoC_min)),
            LuT_RSeries_kOhm_n32=[int((2**32 * 1e-3) * y) for y in R_series_LuT],
        )


# TODO: move code below to sim, LUT only needed by last model


class LUT(BaseModel):
    """Dynamic look-up table that can automatically be generated from a function."""

    x_min: float
    y_values: list[float]
    scale: str
    length: int
    # ⤷ TODO: log-scale not used ATM, could be mapped to a gamma-curve (1.0 == linear)

    @classmethod
    def generate(
        cls,
        x_min: float,
        y_fn: Callable,
        lut_size: int = LUT_SIZE,
        scale: str = "linear",
        *,
        optimize_clamp: bool = False,
    ) -> Self:
        """
        Generate a LUT with a specific width from a provided function.

        It has a minimum value, a size / width and a scale (linear / log2).
        y_fnc is a function that takes an argument and produces the lookup value.
        """
        if scale not in ["linear", "log2"]:
            raise ValueError("scale must be 'linear' or 'log2'")

        if scale == "linear":
            offset = 0.5 if optimize_clamp else 1
            x_values = [(i + offset) * x_min for i in range(lut_size)]
        else:
            offset = math.sqrt(2) if optimize_clamp else 1  # TODO: untested
            x_values = [x_min / offset * 2**i for i in range(lut_size)]

        y_values = [y_fn(x) for x in x_values]

        return cls(x_min=x_min, y_values=y_values, scale=scale, length=lut_size)

    def get(self, x_value: float) -> float:
        # future extension: interpolation instead of clamping
        num = int(x_value / self.x_min)
        # ⤷ round() would be more appropriate, but in c/pru its just integer math

        if self.scale == "linear":  # noqa: SIM108
            idx = max(0, num)
        else:
            idx = int(math.log2(num)) if num > 0 else 0

        if idx >= self.length:  # len(self.y_values)
            idx = self.length - 1
        return self.y_values[idx]


class ModelStorage:
    """Abstract base class for storage models."""

    def step(self, I_cell: float) -> tuple[float, float, float]: ...


class ModelKiBaM(ModelStorage):
    """Naive implementation of the full hybrid KiBaM model from the paper."""

    @validate_call
    def __init__(
        self,
        SoC: Annotated[float, Ge(0), Le(1)],
        cfg: VirtualStorageConfig,
        dt_s: Annotated[float, Gt(0)] = 10e-6,
    ) -> None:
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC
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

    def step(self, I_cell: float) -> tuple[float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        # Step 1 verified separately using Figure 4
        # Steps 1 and 2 verified separately using Figure 10
        # Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)

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
        # TODO: might be possible to remove the 2nd branch if
        #       recovery is accelerated while recharging??
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

        return V_cell, SoC_eff, V_OC


class ModelKiBaMPlus(ModelStorage):
    """Hybrid KiBaM model from the paper with certain extensions.

    Modifications:
    1. support rate capacity during charging (Step 1)
    2. support transient tracking during charging (Step 5)
    3. support self discharge (step 2a)
    """

    @validate_call
    def __init__(
        self,
        SoC: Annotated[float, Ge(0), Le(1)],
        cfg: VirtualStorageConfig,
        dt_s: Annotated[float, Gt(0)] = 10e-6,
    ) -> None:
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC
        self.time_s: float = 0

        # Rate capacity effect
        self.C_unavailable: float = 0
        self.C_unavailable_last: float = 0

        # Transient tracking
        self.discharge_last: bool = False

        # Modified transient tracking
        self.V_transient_S: float = 0
        self.V_transient_L: float = 0

    def step(self, I_cell: float) -> tuple[float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step.

        - Step 1 verified separately using Figure 4
        - Steps 1 and 2 verified separately using Figure 10
        - Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)
        """
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
        # TODO: limit to <=1 should NOT be needed, but it was.

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

        return V_cell, SoC_eff, V_OC


class ModelKiBaMSimple(ModelStorage):
    """PRU-optimized model with a set of simplifications.

    Modifications:
    - omit transient voltages (step 4 & 5)
    - omit rate capacity effect (step 1)
    - replace two expensive Fn by LuT (step 3 & 4)
    - add self discharge resistance (step 2a)
    - TODO: add DC-Bias?
    """

    def __init__(
        self,
        SoC: Annotated[float, Ge(0), Le(1)],
        cfg: VirtualStorageConfig,
        dt_s: Annotated[float, Gt(0)] = 10e-6,
        *,
        optimize_clamp: bool = True,
    ) -> None:
        self.dt_s = dt_s  # not used in step, just for simulator
        self.V_OC_LuT: LUT = LUT.generate(
            1.0 / LUT_SIZE, y_fn=cfg.calc_V_OC, lut_size=LUT_SIZE, optimize_clamp=optimize_clamp
        )
        self.R_series_LuT: LUT = LUT.generate(
            1.0 / LUT_SIZE, y_fn=cfg.calc_R_series, lut_size=LUT_SIZE, optimize_clamp=optimize_clamp
        )
        self.Constant_s_per_As: float = dt_s / cfg.q_As
        self.Constant_1_per_Ohm: float = 1.0 / cfg.R_leak_Ohm
        # state
        self.SoC: float = SoC

    def step(self, I_cell: float) -> tuple[float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
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

        return V_cell, SoC_eff, V_OC


class ModelShpCap(ModelStorage):
    """A derived model from shepherd-codebase for comparing KiBaM as capacitor."""

    def __init__(
        self,
        SoC: Annotated[float, Ge(0), Le(1)],
        cfg: VirtualStorageConfig,
        dt_s: Annotated[float, Gt(0)] = 10e-6,
    ) -> None:
        self.dt_s = dt_s  # not used in step, just for simulator
        self.V_intermediate_max_V = cfg.calc_V_OC(1.0)
        C_intermediate_uF = 1e6 * cfg.q_As / self.V_intermediate_max_V
        C_cap_uF = max(C_intermediate_uF, 0.001)
        SAMPLERATE_SPS = 1.0 / dt_s
        self.Constant_s_per_F = 1e6 / (C_cap_uF * SAMPLERATE_SPS)
        self.Constant_1_per_Ohm: float = 1.0 / cfg.R_leak_Ohm
        # state
        self.V_mid_V = cfg.calc_V_OC(SoC)

    def step(self, I_cell: float) -> tuple[float, float, float]:
        # in PRU P_inp and P_out are calculated and combined to determine current
        # similar to: P_sum_W = P_inp_W - P_out_W, I_mid_A = P_sum_W / V_mid_V
        I_mid_A = -I_cell - self.V_mid_V * self.Constant_1_per_Ohm
        dV_mid_V = I_mid_A * self.Constant_s_per_F
        self.V_mid_V += dV_mid_V

        self.V_mid_V = min(self.V_mid_V, self.V_intermediate_max_V)
        self.V_mid_V = max(self.V_mid_V, sys.float_info.min)
        return self.V_mid_V, self.V_mid_V / self.V_intermediate_max_V, self.V_mid_V
