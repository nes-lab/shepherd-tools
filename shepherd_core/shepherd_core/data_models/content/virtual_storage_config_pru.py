"""Generalized virtual energy storage data models (config)."""

from typing import Annotated
from typing import final

from pydantic import Field
from pydantic import PositiveFloat
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.shepherd import ShpModel

from .virtual_storage_config import VirtualStorageConfig

# constants & custom types
TIMESTEP_s_DEFAULT: float = 1.0 / config.SAMPLERATE_SPS
LuT_SIZE_LOG: int = 7
LuT_SIZE: int = 2**LuT_SIZE_LOG
u32 = Annotated[int, Field(ge=0, lt=2**32)]
lut_storage = Annotated[list[u32], Field(min_length=LuT_SIZE, max_length=LuT_SIZE)]


@final
class StoragePRUConfig(ShpModel):
    """Map settings-list to internal state-vars struct StorageConfig.

    NOTE:
      - yaml is based on si-units like nA, mV, ms, uF
      - c-code and py-copy is using nA, uV, ns, nF, fW, raw
      - ordering is intentional and in sync with shepherd/commons.h
    """

    SoC_init_1_n30: u32
    """ ⤷ initial charge of storage """
    Constant_1_per_nA_n60: u32
    """ ⤷ Convert I_charge to delta-SoC with one multiplication."""
    Constant_1_per_uV_n60: u32
    """ ⤷ Leakage - Convert V_OC to delta-SoC with one multiplication.
    Combines prior constant and R_leak, to maximize resolution.
    """
    LuT_VOC_uV_n8: lut_storage
    """⤷ ranges from 3.9 uV to 16.7 V"""
    LuT_RSeries_kOhm_n32: lut_storage
    """⤷ ranges from 233n to 1 kOhm"""

    @classmethod
    @validate_call
    def from_vstorage(
        cls,
        data: VirtualStorageConfig | None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
        *,
        optimize_clamp: bool = True,
    ) -> Self:
        x_off = 0.5 if optimize_clamp else 0.0
        SoC_min = 1.0 / LuT_SIZE
        if data is None:
            data = VirtualStorageConfig.capacitor(C_uF=100, V_rated=10)
        V_OC_LuT = [data.calc_V_OC(SoC_min * (x + x_off)) for x in range(LuT_SIZE)]
        R_series_LuT = [data.calc_R_series(SoC_min * (x + x_off)) for x in range(LuT_SIZE)]
        Constant_1_per_A: float = dt_s / data.q_As
        Constant_1_per_V: float = Constant_1_per_A / data.R_leak_Ohm
        return cls(
            SoC_init_1_n30=round(2**30 * data.SoC_init),
            Constant_1_per_nA_n60=round((2**60 / 1e9) * Constant_1_per_A),
            Constant_1_per_uV_n60=round((2**60 / 1e6) * Constant_1_per_V),
            LuT_VOC_uV_n8=[round((2**8 * 1e6) * y) for y in V_OC_LuT],
            LuT_RSeries_kOhm_n32=[round((2**32 * 1e-3) * y) for y in R_series_LuT],
        )
