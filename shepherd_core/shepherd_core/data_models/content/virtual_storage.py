
from typing import Annotated, Callable
from typing import Any

from pydantic import Field, BaseModel
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.calibration_hw_def import V_REF_ADC
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client
import copy
import sys
import math
from itertools import product


class VirtualStorageConfig(ContentModel, title="Config for the virtual energy storage"):
    """ Battery model based on two papers.

    Model An Accurate Electrical Battery Model Capable of Predicting Runtime and I–V Performance
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf

    A Hybrid Battery Model Capable of Capturing Dynamic Circuit Characteristics and Nonlinear Capacity Effects
    https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1210&context=electricalengineeringfacpub
    """
    # Capacity:
    C: float = 0  # TODO: _As
    """ ⤷ Capacity """
    # Model parameters:
    a0 = 0
    a1 = 0
    a2 = 0
    a3 = 0
    a4 = 0
    a5 = 0
    b0 = 0
    b1 = 0
    b2 = 0
    b3 = 0
    b4 = 0
    b5 = 0
    c0 = 0
    c1 = 0
    c2 = 0
    d0 = 0
    d1 = 0
    d2 = 0
    e0 = 0
    e1 = 0
    e2 = 0
    f0 = 0
    f1 = 0
    f2 = 0
    # TODO: replace with, p_SoC, p_Rs, p_RtS, Cts, RtL
    a: Annotated[list[float], Field(min_length=6,max_length=6)] = [0, 0, 0, 1, 0, 0]  # direct SOC-Mapping
    """ ⤷ Parameters for SoC-Mapping """
    b: Annotated[list[float], Field(min_length=6,max_length=6)] = [0,0,0,0,0,0]  # no resistance
    """ ⤷ Parameters for series-resistance """
    cl: Annotated[list[float], Field(min_length=3,max_length=3)] = [0,0,0]  # no transient
    """ ⤷ Parameters for R_transient_S (short-term) """
    d: Annotated[list[float], Field(min_length=3,max_length=3)] = [0,0,0]  # no transient
    """ ⤷ Parameters for C_transient_S (short-term)"""
    e: Annotated[list[float], Field(min_length=3,max_length=3)] = [0,0,0]  # no transient
    """ ⤷ Parameters for R_transient_L (long-term)"""
    f: Annotated[list[float], Field(min_length=3,max_length=3)] = [0,0,0]  # no transient
    """ ⤷ Parameters for C_transient_L (long-term)"""

    c: float = 0  # TODO: default to 1? rename to cre?
    """ ⤷ rate capacity effect - Set to 1 to disregard """
    kdash: float = 0

    # Custom parameters
    name: str = ''  # TODO: already in ContentModel
    r_self_discharge: float = sys.float_info.max  # TODO: is this modeled? r_parallel

    @classmethod
    def lipo(cls, capacity_mAh: float) -> Self:
        """ Modeled after the PL-383562 Polymer Lithium-ion Battery.

        https://www.batteryspace.com/prod-specs/pl383562.pdf

        """
        return cls(
            name=f'{capacity_mAh} mAh LiPo',
            # Capacity:  # TODO: is it really capacity? seems to be electrical charge q_As
            C=capacity_mAh * 3600 / 1000,  # in [As], example: 860 mAh => 3096 As
            a=[-0.852, 63.867, 3.6297, 0.559, 0.51, 0.508],
            b = [0.1463, 30.27, 0.1037, 0.0584, 0.1747, 0.1288],
            cl = [0.1063, 62.49, 0.0437],
            d = [-200, 128, 300], # TODO d1 most likely a mistake in the paper!
            e = [0.0712, 61.4, 0.0288],
            f = [-3083, 180, 5088],
            # params.y10 = 2863.3 # unused
            # params.y20 = 232.66 # unused
            c = 0.9248,
            kdash = 0.0008,
            # content-fields
            description="", # TODO
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )


    @classmethod
    def lead(cls, capacity_mAh: float) -> Self:
        """ Modeled after the LEOCH LP12-1.2AH lead acid battery.

        https://www.leoch.com/pdf/reserve-power/agm-vrla/lp-general/LP12-1.2.pdf
        """
        return cls(
            name=f'{capacity_mAh} mAh Lead-Acid',
            C = capacity_mAh * 3600 / 1000, # TODO: params
            # content-fields
            description="",  # TODO
            owner="NES Lab",
            group="NES Lab",
            visible2group=True,
            visible2all=True,
        )


    @classmethod
    def mlcc(cls, capacity_uF: float, R_series_Ohm: float = 0) -> Self:
        return cls(
            name=f'{capacity_uF} uF MLCC',
            C = capacity_uF, # TODO, capacity_As = uF * V
            a = [0, 0, 0, 1, 0, 0],  # direct SOC-Mapping
            b = [0, 0, R_series_Ohm, 0, 0, 0],  # const series resistance
            cl = [0,0,0],  # no R_transient_S
            d = [0,0,0],  # no C_transient_S
            e = [0,0,0],  # no R_transient_L
            f = [0,0,0],  # no C_transient_L
            # content-fields
            description="",  # TODO
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

    def without_rate_capacity(self):  # TODO: still needed?
        result = copy.deepcopy(self)
        result.c = 1
        result.name += ' no_rate_cap'
        return result

    def without_transient_voltages(self):  # TODO: still needed?
        result = copy.deepcopy(self)
        result.d2 = sys.float_info.max
        result.f2 = sys.float_info.max
        result.name += ' no_tran_vs'
        return result

    def with_self_discharge_experiment(self, duration, final_soc):  # TODO: still needed?
        # Example: 50mAh; SoC from 100 % to 85 % over 30 days => ~88.605 kOhm
        result = copy.deepcopy(self)
        result.r_self_discharge = duration / (-math.log(final_soc, math.e) * self.C)
        result.name += f' r_leak={result.r_self_discharge}'
        return result


    def V_OC(self, SoC: float) -> float:
        return (self.a[0] * math.pow(math.e, -self.a[1] * SoC)
                + self.a[2]
                + self.a[3] * SoC
                - self.a[4] * SoC ** 2
                + self.a[5] * SoC ** 3)


    def R_series(self, SoC: float) -> float:
        return (self.b[0] * math.pow(math.e, -self.b[1] * SoC)
                + self.b[2]
                + self.b[3] * SoC
                - self.b[4] * SoC ** 2
                + self.b[5] * SoC ** 3)

    def R_transient_S(self, SoC: float) -> float:
        return self.cl[0] * math.pow(math.e, -self.cl[1] * SoC) + self.cl[2]

    def C_transient_S(self, SoC: float) -> float:
        return self.d[0] * math.pow(math.e, -self.d[1] * SoC) + self.d[2]

    def R_transient_L(self, SoC: float) -> float:
        return self.e[0] * math.pow(math.e, -self.e[1] * SoC) + self.e[2]

    def C_transient_L(self, SoC: float) -> float:
        return self.f[0] * math.pow(math.e, -self.f[1] * SoC) + self.f[2]



# custom types
LUT_SIZE = 128
u32 = Annotated[int, Field(ge=0, lt=2**32)]
lut_storage = Annotated[list[u32], Field(min_length=LUT_SIZE, max_length=LUT_SIZE)]

class LUT(BaseModel):

    x_min: float
    y_values: list[float]
    scale: str  # TODO: Enum?
    length: int

    @classmethod
    def generate(cls, x_min: float, y_fn: Callable, lut_size: int = LUT_SIZE, scale: str = "linear", *, optimize_clamp: bool = True):
        """
        Generates an n-dimensional LUT where n is the length of the input arrays.
        Each dimension has a minimum value, a size and a scale (lin / log2).
        y_fnc is a function that takes n arguments and produces the lookup value.
        """
        if scale not in ["linear", "log2"]:
            raise ValueError(f"scale must be 'linear' or 'log2'")

        if scale == 'linear':
            offset = 0.5 if optimize_clamp else 1
            x_values = [(i + offset) * x_min for i in range(lut_size)]
        else:
            offset = math.sqrt(2) if optimize_clamp else 1 # TODO untested
            x_values = [x_min / offset * 2**i for i in range(lut_size)]

        y_values = [y_fn(x) for x in x_values]  # TODO: could be simplified further, skipping x_values

        return cls(x_min=x_min, y_values=y_values, scale=scale, length=lut_size)


    def get(self, x_value: float, interpolate='clamp'):
        # TODO: interpolation not implemented ATM
        # TODO: log-scale not used ATM, could be mapped to a gamma-curve (1.0 == linear)
        num = int(x_value / self.x_min)
        if self.scale == 'linear':
            idx = num if num > 0 else 0
        else:
            idx = int(math.log2(num)) if num > 0 else 0

        if idx >= len(self.y_values):
            idx = len(self.y_values) - 1
        return self.y_values[idx]


class StoragePRUConfig(ShpModel):

    Constant_s_per_mAs_n48: u32
    Constant_1_per_kOhm_n18: u32
    LUT_voc_SoC_min_log2_u_n32: u32   # TODO: VOC, why _u_
    LUT_voc_uV_n8: lut_storage
    LUT_rseries_SoC_min_log2_u_n32: u32  # TODO: RSeries
    LUT_rseries_KOhm_n32: lut_storage  # TODO: kOhm ?

    @classmethod
    def from_vstorage(
        cls,
        data: VirtualStorageConfig,
    ) -> Self:
        return cls()



# TODO: move code below to sim

class ModelNaive:
    """
    Calculates the battery SoC and terminal voltage after drawing a current i_cell over a period of dt
    Implements the hybrid KiBaM model from the paper with certain modifications:
    1. support rate capacity during charging (Step 1)
    2. support transient tracking during charging (Step 5)
    3. support self discharge (step 2a)
    """

    def __init__(self, SoC: float, cfg: VirtualStorageConfig, dt_s: float = 10e-6) -> None:
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s: float = dt_s
        # state
        self.SoC: float = SoC # TODO: SoC, clamp to 0..1
        self.time_s: float = 0

        # Rate capacity effect
        self.C_unavailable: float = 0
        self.C_unavailable_last: float = 0

        # Transient tracking
        self.V_transient_S_max: float = 0  # TODO: S, L
        self.V_transient_L_max: float = 0
        self.discharge_last: bool = False

        # Modified transient tracking
        self.V_transient_S: float = 0
        self.V_transient_L: float = 0

    def step(self, I_cell: float) -> tuple[float, float, float]:
        """
        Calculates the battery SoC and terminal voltage after drawing a current i_cell over a period of dt
        Naive implementation of the full hybrid KiBaM model from the paper
        """

        # Step 1 verified separately using Figure 4
        # Steps 1 and 2 verified separately using Figure 10
        # Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)

        # Step 0: Determine whether battery is charging or resting and calculate time since last switch
        if self.discharge_last != (I_cell > 0):  # Reset time delta when current sign changes
            self.discharge_last = I_cell > 0
            self.time_s = 0
            self.C_unavailable_last = self.C_unavailable # Save C_unavailable at time of switch

        self.time_s += self.dt_s  # Consider time delta including this iteration (since we want v_trans after the current step)

        # Step 1: Calculate unavailable capacity after dt (due to rate capacity and recovery effect) (equation 17)
        # TODO might be possible to remove the 2nd branch if recovery is accelerated while recharging??
        if I_cell > 0:  # Discharging
            self.C_unavailable = self.C_unavailable_last * math.pow(math.e, -self.cfg.kdash * self.time_s) + (
                        1 - self.cfg.c) * I_cell / self.cfg.c * (1 - math.pow(math.e, -self.cfg.kdash * self.time_s)) / self.cfg.kdash
        else:  # Recovering
            self.C_unavailable = self.C_unavailable_last * math.pow(math.e, -self.cfg.kdash * self.time_s)

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        self.SoC = self.SoC - 1 / self.cfg.C * (I_cell * self.dt_s)
        SoC_eff = self.SoC - 1 / self.cfg.C * self.C_unavailable

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


class ModelFull:
    """
    Calculates the battery SoC and terminal voltage after drawing a current i_cell over a period of dt
    Implements the hybrid KiBaM model from the paper with certain modifications:
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
        # Step 1 verified separately using Figure 4
        # Steps 1 and 2 verified separately using Figure 10
        # Complete model verified using Figures 8 (a, b) and Figure 9 (a, b)

        # Step 0: Determine whether battery is charging or resting and calculate time since last switch
        if self.discharge_last != (I_cell > 0):  # Reset time delta when current sign changes
            self.discharge_last = I_cell > 0
            self.time_s = 0
            self.C_unavailable_last = self.C_unavailable # Save C_unavailable at time of switch

        self.time_s += self.dt_s  # Consider time delta including this iteration (since we want v_trans after the current step)

        # Step 1: Calculate unavailable capacity after dt (due to rate capacity and recovery effect) (equation 17)
        # TODO if this should be used in production, additional verification is required (analytically derive versions of
        #                               equations 16/17 without time range restrictions)
        self.C_unavailable = self.C_unavailable_last * math.pow(math.e, -self.cfg.kdash * self.time_s) + (
                    1 - self.cfg.c) * I_cell / self.cfg.c * (1 - math.pow(math.e, -self.cfg.kdash * self.time_s)) / self.cfg.kdash

        # Step 2a: Calculate and add self-discharge current
        I_leak = self.SoC / self.cfg.r_self_discharge
        I_cell += I_leak

        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        self.SoC = self.SoC - 1 / self.cfg.C * (I_cell * self.dt_s)
        SoC_eff = self.SoC - 1 / self.cfg.C * self.C_unavailable

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
        self.V_transient_S = R_transient_S * I_cell + (self.V_transient_S - R_transient_S * I_cell) * math.pow(math.e, -self.dt_s / tau_S)
        self.V_transient_L = R_transient_L * I_cell + (self.V_transient_L - R_transient_L * I_cell) * math.pow(math.e, -self.dt_s / tau_L)

        # Step 6: Calculate cell voltage (equations 8 and 9)
        V_transient = self.V_transient_S + self.V_transient_L
        V_cell = V_OC - I_cell * R_series - V_transient

        return V_cell, SoC_eff, V_OC

class ModelLUTNoTransient:
    """
    Calculates the battery SoC and terminal voltage after drawing a current i_cell over a period of dt
    MODIFIED model to omit transient voltages AND omit rate capacity effect
    """

    def __init__(self, SoC: float, cfg: VirtualStorageConfig, dt_s: float = 10e-6):
        self.V_OC_LuT: LUT = LUT.generate(1.0 / LUT_SIZE, y_fn=cfg.V_OC, lut_size=LUT_SIZE, optimize_clamp=False)
        self.R_series_LuT: LUT = LUT.generate(1.0 / LUT_SIZE, y_fn=cfg.R_series, lut_size=LUT_SIZE, optimize_clamp=False)
        self.Constant_s_per_As: float = dt_s / cfg.C
        # self.Constant_1_per_kOhm_n18: float # TODO: leakage?
        # state
        self.SoC: float = SoC

    def step(self, I_cell: float) -> tuple[float, float, float]:
        # Step 2: Calculate SoC after dt (equation 6; modified for discrete operation)
        # SoC = SoC - 1 / C * (i_cell * dt)
        self.SoC = self.SoC - I_cell * self.Constant_s_per_As
        SoC_eff = self.SoC  # MODIFIED: removed term due to omission of rate capacity effect

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