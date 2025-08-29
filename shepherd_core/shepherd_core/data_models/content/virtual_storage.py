"""Generalized virtual energy storage data models (config)."""

import math
import sys
from collections.abc import Sequence
from datetime import timedelta
from typing import Annotated
from typing import Any

from annotated_types import Ge
from annotated_types import Gt
from annotated_types import Le
from pydantic import Field
from pydantic import NonNegativeFloat
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client

soc_t = Annotated[float, Ge(0.0), Le(1.0)]
# TODO: adapt V_max in vsrc,


class VirtualStorageConfig(ContentModel, title="Config for the virtual energy storage"):
    """KiBaM Battery model based on two papers.

    Model An Accurate Electrical Battery Model Capable
        of Predicting Runtime and I-V Performance
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf

    A Hybrid Battery Model Capable of Capturing Dynamic Circuit
        Characteristics and Nonlinear Capacity Effects
    https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1210&context=electricalengineeringfacpub
    """

    SoC_init: soc_t = 1.0
    """ ⤷ State of Charge that is available when emulation starts."""

    q_As: PositiveFloat
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
    kdash: PositiveFloat = sys.float_info.min  # TODO: use k directly?
    """ ⤷ Parameter for rate capacity effect
        - temporary component of rate capacity effect, valve in KiBaM (eq 17)
        - k' = k/c(1-c),
        """

    R_leak_Ohm: PositiveFloat = sys.float_info.max
    """ ⤷ Parameter for self discharge (custom extension)
        - effect is often very small, mostly relevant for some capacitors
        """

    @classmethod
    @validate_call
    def lipo(cls, capacity_mAh: PositiveFloat, SoC_init: soc_t = 1.0) -> Self:
        """Modeled after the PL-383562 2C Polymer Lithium-ion Battery.

        Nominal Voltage     3.7 V
        Nominal Capacity    860 mAh
        Discharge Cutoff    3.0 V
        Charge Cutoff       4.2 V
        Max Discharge       2 C / 1.72 A
        https://www.batteryspace.com/prod-specs/pl383562.pdf

        """
        return cls(
            SoC_init=SoC_init,
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
    def lead_acid(cls, capacity_mAh: PositiveFloat, SoC_init: soc_t = 1.0) -> Self:
        """Modeled after the LEOCH LP12-1.2AH lead acid battery.

        Nominal Voltage     12 V
        Nominal Capacity    1.2 Ah
        Discharge Cutoff    10.8 V
        Charge Cutoff       13.5 V
        Max Discharge       15 C / 18 A
        https://www.leoch.com/pdf/reserve-power/agm-vrla/lp-general/LP12-1.2.pdf
        """
        return cls(
            SoC_init=SoC_init,
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
        C_uF: PositiveFloat,
        V_rated: PositiveFloat,
        SoC_init: soc_t = 1.0,
        R_series_Ohm: NonNegativeFloat = 0.0,
        R_leak_Ohm: PositiveFloat = sys.float_info.max,
    ) -> Self:
        return cls(
            SoC_init=SoC_init,
            q_As=1e-6 * C_uF * V_rated,
            p_VOC=[0, 0, 0, V_rated, 0, 0],  # 100% SoC is @V_rated,
            # no transients per default
            p_Rs=[0, 0, R_series_Ohm, 0, 0, 0],  # const series resistance
            R_leak_Ohm=R_leak_Ohm,
            # content-fields below
            name=f"Capacitor {C_uF:.0f} uF",
            description="Model of a Capacitor with [DC-Bias], series & leakage resistor",
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )
        # TODO: add model DC-Bias via p_VOC?

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
        model_dict = self.model_dump()
        model_dict["p_rce"] = 1
        model_dict["name"] += " no_rate_cap"
        return type(self)(**model_dict)

    def without_transient_voltages(self) -> Self:
        model_dict = self.model_dump()
        model_dict["p_RtS"] = [0, 0, 0]
        model_dict["p_CtS"] = [0, 0, 0]
        model_dict["p_RtL"] = [0, 0, 0]
        model_dict["p_CtL"] = [0, 0, 0]
        model_dict["name"] += " no_transient_vs"
        return type(self)(**model_dict)

    @staticmethod
    @validate_call
    def calc_k(kdash: PositiveFloat, c: Annotated[float, Gt(0), Le(1)]) -> float:
        """Translate between k & k'.

        As explained below equation 4 in paper: k' = k / (c * (c - 1))
        """
        return kdash * c * (1 - c)

    @property
    def kdash_(self) -> float:
        return self.k / (self.p_rce * (self.p_rce - 1))

    @validate_call
    def calc_R_self_discharge(
        self,
        duration: timedelta,
        SoC_final: Annotated[float, Ge(0), Le(1)],
        SoC_0: Annotated[float, Ge(0), Le(1)] = 1.0,
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


# constants & custom types
TIMESTEP_s_DEFAULT = 1.0 / config.SAMPLERATE_SPS
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

    SoC_init_1u: u32
    Constant_us_per_nAs_n40: u32
    Constant_1_per_kOhm_n18: u32
    LuT_SoC_min_log2_1u: u32
    LuT_VOC_uV_n8: lut_storage
    """⤷ ranges from 3.9 uV to 16.7 V"""
    LuT_RSeries_kOhm_n32: lut_storage
    """⤷ ranges from 233n to 1 kOhm"""

    @classmethod
    @validate_call
    def from_vstorage(
        cls,
        data: VirtualStorageConfig,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
        *,
        optimize_clamp: bool = True,
    ) -> Self:
        x_off = 0.5 if optimize_clamp else 1.0
        LuT_SoC_min = 1.0 / LUT_SIZE
        V_OC_LuT = [data.calc_V_OC(LuT_SoC_min * (x + x_off)) for x in range(LUT_SIZE)]
        R_series_LuT = [data.calc_R_series(LuT_SoC_min * (x + x_off)) for x in range(LUT_SIZE)]
        Constant_s_per_As: float = dt_s / data.q_As
        Constant_1_per_Ohm: float = 1.0 / data.R_leak_Ohm
        return cls(
            SoC_init_1u=round(data.SoC_init * 1e6),
            Constant_us_per_nAs_n40=round((2**40 / 1e3) * Constant_s_per_As),
            Constant_1_per_kOhm_n18=round((2**18 / 1e-3) * Constant_1_per_Ohm),
            LuT_SoC_min_log2_1u=round(math.log2(1e6 * LuT_SoC_min)),
            LuT_VOC_uV_n8=[round((2**8 * 1e6) * y) for y in V_OC_LuT],
            LuT_RSeries_kOhm_n32=[round((2**32 * 1e-3) * y) for y in R_series_LuT],
        )
