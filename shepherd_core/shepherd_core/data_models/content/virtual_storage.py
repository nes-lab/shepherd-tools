"""Generalized virtual energy storage data models (config)."""

import copy
import math
import sys
from collections.abc import Callable
from collections.abc import Sequence
from typing import Annotated
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client


class VirtualStorageConfig(ContentModel, title="Config for the virtual energy storage"):
    """Battery model based on two papers.

    Model An Accurate Electrical Battery Model Capable
        of Predicting Runtime and I-V Performance
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf

    A Hybrid Battery Model Capable of Capturing Dynamic Circuit
        Characteristics and Nonlinear Capacity Effects
    https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1210&context=electricalengineeringfacpub
    """

    C_As: float  # TODO: is it really capacity? seems to be electrical charge q_As
    """ ⤷ Capacity """
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

    p_rce: float = 1.0
    """ ⤷ rate capacity effect
        - Set to 1 to disregard
        - named c in paper
        """
    kdash: float = 0  # TODO: description, renaming?

    # Custom parameter extension
    R_self_discharge: float = sys.float_info.max
    # TODO: is this modeled? r_parallel? code suggests its not Ohm but 1/A
    #       maybe name it p_self_discharge_1_per_A

    @classmethod
    def lipo(cls, capacity_mAh: float) -> Self:
        """Modeled after the PL-383562 2C Polymer Lithium-ion Battery.

        Nominal Voltage     3.7 V
        Nominal Capacity    860 mAh
        Discharge Cutoff    3.0 V
        Charge Cutoff       4.2 V
        Max Discharge       2 C / 1.72 A
        https://www.batteryspace.com/prod-specs/pl383562.pdf

        """
        return cls(
            C_As=capacity_mAh * 3600 / 1000,  # in [As], example: 860 mAh => 3096 As
            p_VOC=[-0.852, 63.867, 3.6297, 0.559, 0.51, 0.508],
            p_Rs=[0.1463, 30.27, 0.1037, 0.0584, 0.1747, 0.1288],
            p_RtS=[0.1063, 62.49, 0.0437],
            p_CtS=[-200, 128, 300],  # TODO: d1=-138 most likely a mistake in the table/paper!
            p_RtL=[0.0712, 61.4, 0.0288],
            p_CtL=[-3083, 180, 5088],
            # y10 = 2863.3, y20 = 232.66 # unused
            p_rce=0.9248,
            kdash=0.0008,
            # content-fields
            name=f"{capacity_mAh} mAh LiPo",
            description="",  # TODO: fill
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @classmethod
    def lead_acid(cls, capacity_mAh: float) -> Self:
        """Modeled after the LEOCH LP12-1.2AH lead acid battery.

        Nominal Voltage     12 V
        Nominal Capacity    1.2 Ah
        Discharge Cutoff    10.8 V
        Charge Cutoff       13.5 V
        Max Discharge       15 C / 18 A
        https://www.leoch.com/pdf/reserve-power/agm-vrla/lp-general/LP12-1.2.pdf
        """
        return cls(
            C_As=capacity_mAh * 3600 / 1000,
            p_VOC=[5.429, 117.5, 11.32, 2.706, 2.04, 1.026],
            p_Rs=[1.578, 8.527, 0.7808, -1.887, -2.404, -0.649],
            p_RtS=[2.771, 9.079, 0.22],
            p_CtS=[-2423, 75.14, 55],
            p_RtL=[2.771, 9.079, 0.218],  # TODO: first 2 are identical with p_RtS in table/paper
            p_CtL=[-1240, 9.571, 3100],
            # y10 = 2592, y20 = 1728 # unused
            p_rce=0.6,
            kdash=0.0034,
            # content-fields
            name=f"{capacity_mAh} mAh Lead-Acid",
            description="",  # TODO: fill
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @classmethod
    def mlcc(cls, capacity_uF: float, R_series_Ohm: float = 0) -> Self:
        return cls(
            C_As=capacity_uF,  # TODO: capacity_As = uF * V
            # direct SOC-Mapping & no transients per default
            p_Rs=[0, 0, R_series_Ohm, 0, 0, 0],  # const series resistance
            # content-fields
            name=f"{capacity_uF} uF MLCC",
            description="",  # TODO: fill
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        values, chain = tb_client.try_completing_model(cls.__name__, values)
        values = tb_client.fill_in_user_data(values)
        log.debug("vStorage-Inheritances: %s", chain)
        return values

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        return self

    def without_rate_capacity(self) -> Self:
        # ⤷ TODO: won't work ATM, still needed?
        result = copy.deepcopy(self)
        result.p_rce = 1
        result.name += " no_rate_cap"
        return result

    def without_transient_voltages(self) -> Self:
        # ⤷ TODO: won't work ATM, still needed?
        result = copy.deepcopy(self)
        result.d2 = sys.float_info.max
        result.f2 = sys.float_info.max
        result.name += " no_tran_vs"
        return result

    def with_self_discharge_experiment(self, duration: float, final_soc: float) -> Self:
        # ⤷ TODO: won't work ATM, still needed?
        # Example: 50mAh; SoC from 100 % to 85 % over 30 days => ~88.605 kOhm
        result = copy.deepcopy(self)
        result.R_self_discharge = duration / (-math.log(final_soc) * self.C_As)
        # ⤷ TODO: is no resistance, but 1/A
        result.name += f" r_leak={result.R_self_discharge}"
        return result

    def V_OC(self, SoC: float) -> float:
        return (
            self.p_VOC[0] * math.pow(math.e, -self.p_VOC[1] * SoC)
            + self.p_VOC[2]
            + self.p_VOC[3] * SoC
            - self.p_VOC[4] * SoC**2
            + self.p_VOC[5] * SoC**3
        )

    def R_series(self, SoC: float) -> float:
        return (
            self.p_Rs[0] * math.pow(math.e, -self.p_Rs[1] * SoC)
            + self.p_Rs[2]
            + self.p_Rs[3] * SoC
            - self.p_Rs[4] * SoC**2
            + self.p_Rs[5] * SoC**3
        )

    def R_transient_S(self, SoC: float) -> float:
        return self.p_RtS[0] * math.pow(math.e, -self.p_RtS[1] * SoC) + self.p_RtS[2]

    def C_transient_S(self, SoC: float) -> float:
        return self.p_CtS[0] * math.pow(math.e, -self.p_CtS[1] * SoC) + self.p_CtS[2]

    def R_transient_L(self, SoC: float) -> float:
        return self.p_RtL[0] * math.pow(math.e, -self.p_RtL[1] * SoC) + self.p_RtL[2]

    def C_transient_L(self, SoC: float) -> float:
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

    Constant_s_per_mAs_n48: u32  # TODO: how n48?
    Constant_1_per_kOhm_n18: u32
    LuT_VOC_SoC_min_log2_u_n32: u32  # TODO: why _u_, just for 1e-6? and why n32?
    LuT_VOC_uV_n8: lut_storage
    LuT_RSeries_SoC_min_log2_u_n32: u32
    LuT_RSeries_kOhm_n32: lut_storage

    @classmethod
    def from_vstorage(cls, data: VirtualStorageConfig, *, optimize_clamp: bool = False) -> Self:
        x_off = 0.5 if optimize_clamp else 1.0
        LuT_VOC_SoC_min = 1.0 / LUT_SIZE
        V_OC_LuT = [data.V_OC(LuT_VOC_SoC_min * (x + x_off)) for x in range(LUT_SIZE)]
        LuT_RSeries_SoC_min = 1.0 / LUT_SIZE
        R_series_LuT = [data.R_series(LuT_RSeries_SoC_min * (x + x_off)) for x in range(LUT_SIZE)]
        Constant_s_per_As: float = 10e-6 / data.C_As
        Constant_1_per_Ohm: float = 1.0 / data.R_self_discharge  # TODO: Probably wrong
        return cls(
            Constant_s_per_mAs_n48=int((2**48 / 1e3) * Constant_s_per_As),
            Constant_1_per_kOhm_n18=int((2**18 / 1e-3) * Constant_1_per_Ohm),
            LuT_VOC_SoC_min_log2_u_n32=int((2**32 / 1e6) * LuT_VOC_SoC_min),  # TODO: log2-part
            LuT_VOC_uV_n8=[int((2**8 / 1e6) * y) for y in V_OC_LuT],
            LuT_RSeries_SoC_min_log2_u_n32=int((2**32 / 1e6) * LuT_RSeries_SoC_min),
            # ⤷ TODO: log2-part
            LuT_RSeries_kOhm_n32=[int((2**32 / 1e-3) * y) for y in R_series_LuT],
        )  # TODO: probably wrong


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
        # TODO: could be simplified further, skipping x_values

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


class ModelNaive:  # TODO: rename ModelKiBaM
    """Naive implementation of the full hybrid KiBaM model from the paper."""

    def __init__(self, SoC: float, cfg: VirtualStorageConfig, dt_s: float = 10e-6) -> None:
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC  # TODO: clamp to 0..1?
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
        self.SoC = self.SoC - 1 / self.cfg.C_As * (I_cell * self.dt_s)
        SoC_eff = self.SoC - 1 / self.cfg.C_As * self.C_unavailable

        # Step 3: Calculate V_OC after dt (equation 7)
        V_OC = self.cfg.V_OC(SoC_eff)

        # Step 4: Calculate resistance and capacitance values after dt (equation 12)
        R_series = self.cfg.R_series(SoC_eff)
        R_transient_S = self.cfg.R_transient_S(SoC_eff)
        C_transient_S = self.cfg.C_transient_S(SoC_eff)
        R_transient_L = self.cfg.R_transient_L(SoC_eff)
        C_transient_L = self.cfg.C_transient_L(SoC_eff)

        # Step 5: Calculate transient voltages (equations 10 and 11)
        tau_S = R_transient_S * C_transient_S
        if I_cell > 0:  # Discharging
            V_transient_S = R_transient_S * I_cell * (1 - math.pow(math.e, -self.time_s / tau_S))
            self.V_transient_S_max = V_transient_S
        else:  # Recovering
            V_transient_S = self.V_transient_S_max * math.pow(math.e, -self.time_s / tau_S)

        tau_L = R_transient_L * C_transient_L
        if I_cell > 0:  # Discharging
            V_transient_L = R_transient_L * I_cell * (1 - math.pow(math.e, -self.time_s / tau_L))
            self.V_transient_L_max = V_transient_L
        else:  # Recovering
            V_transient_L = self.V_transient_L_max * math.pow(math.e, -self.time_s / tau_L)

        # Step 6: Calculate cell voltage (equations 8 and 9)
        V_transient = V_transient_S + V_transient_L
        V_cell = V_OC - I_cell * R_series - V_transient

        return V_cell, SoC_eff, V_OC


class ModelFull:  # TODO: rename ModelKiBaMExtended ?
    """Hybrid KiBaM model from the paper with certain extensions.

    Modifications:
    1. support rate capacity during charging (Step 1)
    2. support transient tracking during charging (Step 5)
    3. support self discharge (step 2a)
    """

    def __init__(self, SoC: float, cfg: VirtualStorageConfig, dt_s: float = 10e-6) -> None:
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
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        # Step 1 verified separately using Figure 4
        # Steps 1 and 2 verified separately using Figure 10
        # Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)

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

        # Step 2a: Calculate and add self-discharge current
        I_leak = self.SoC / self.cfg.R_self_discharge
        # ⤷ TODO: is that correct? n / Ohm != A, but it seems [Rsd]=1/A
        I_cell += I_leak

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        self.SoC = self.SoC - 1 / self.cfg.C_As * (I_cell * self.dt_s)
        SoC_eff = self.SoC - 1 / self.cfg.C_As * self.C_unavailable

        # Step 3: Calculate V_OC after dt (equation 7)
        V_OC = self.cfg.V_OC(SoC_eff)

        # Step 4: Calculate resistance and capacitance values after dt (equation 12)
        R_series = self.cfg.R_series(SoC_eff)
        R_transient_S = self.cfg.R_transient_S(SoC_eff)
        C_transient_S = self.cfg.C_transient_S(SoC_eff)
        R_transient_L = self.cfg.R_transient_L(SoC_eff)
        C_transient_L = self.cfg.C_transient_L(SoC_eff)

        # Step 5: Calculate transient voltages (equations 10 and 11)
        tau_S = R_transient_S * C_transient_S
        tau_L = R_transient_L * C_transient_L
        self.V_transient_S = R_transient_S * I_cell + (
            self.V_transient_S - R_transient_S * I_cell
        ) * math.pow(math.e, -self.dt_s / tau_S)
        self.V_transient_L = R_transient_L * I_cell + (
            self.V_transient_L - R_transient_L * I_cell
        ) * math.pow(math.e, -self.dt_s / tau_L)

        # Step 6: Calculate cell voltage (equations 8 and 9)
        V_transient = self.V_transient_S + self.V_transient_L
        V_cell = V_OC - I_cell * R_series - V_transient

        return V_cell, SoC_eff, V_OC


class ModelLUTNoTransient:  # TODO: rename ModelPRU
    """PRU-optimized model with a set of simplifications.

    Modifications:
    - omit transient voltages
    - omit rate capacity effect.
    - replace
    - TODO: add self discharge
    - TODO: add DC-Bias?
    """

    def __init__(
        self,
        SoC: float,
        cfg: VirtualStorageConfig,
        dt_s: float = 10e-6,
        *,
        optimize_clamp: bool = False,
    ) -> None:
        self.V_OC_LuT: LUT = LUT.generate(
            1.0 / LUT_SIZE, y_fn=cfg.V_OC, lut_size=LUT_SIZE, optimize_clamp=optimize_clamp
        )
        self.R_series_LuT: LUT = LUT.generate(
            1.0 / LUT_SIZE, y_fn=cfg.R_series, lut_size=LUT_SIZE, optimize_clamp=optimize_clamp
        )
        self.Constant_s_per_As: float = dt_s / cfg.C_As
        self.Constant_1_per_kOhm: float = sys.float_info.max  # TODO: leakage seems to be missing?
        # state
        self.SoC: float = SoC

    def step(self, I_cell: float) -> tuple[float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        #       = SoC - 1 / C * (i_cell * dt)
        SoC_eff = self.SoC = self.SoC - I_cell * self.Constant_s_per_As
        # ⤷ MODIFIED: removed term due to omission of rate capacity effect

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
        V_cell = V_OC - I_cell * R_series

        return V_cell, SoC_eff, V_OC
