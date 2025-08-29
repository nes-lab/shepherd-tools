"""this is ported py-version of the pru-code.

Goals:

- stay close to original code-base
- offer a comparison for the tests
- step 1 to a virtualization of emulation

NOTE1: DO NOT OPTIMIZE -> stay close to original c-code-base
NOTE2: adc-harvest-routines are not part of this model (virtual_harvester lines 66:289)

Compromises:

- Py has to map the settings-list to internal vars -> is kernel-task
- Python has no static vars -> FName_reset is handling the class-vars

"""

from pydantic import PositiveFloat
from pydantic import validate_call

from shepherd_core import log
from virtual_storage import StoragePRUConfig, LUT_SIZE
from virtual_storage import TIMESTEP_s_DEFAULT
from virtual_storage import VirtualStorageConfig
from virtual_storage import soc_t


class ModelStorage:
    """Abstract base class for storage models."""

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]: ...

def u32s(i: float) -> int:
    if i > 2**32:
        log.warning("u32-overflow")
    if i < 0:
        log.warning("u32-underflow")
    return int(min(max(i,0), 2**32))

def u64s(i: float) -> int:
    if i > 2**64:
        log.warning("u64-overflow")
    if i < 0:
        log.warning("u64-underflow")
    return int(min(max(i,0), 2**64))

class VirtualStorageModel(ModelStorage):
    """Ported python version of the pru vStorage.

    This model should behave like ModelKiBaMSimple
    """

    @validate_call
    def __init__(
        self,
        cfg: VirtualStorageConfig,
        SoC_init: soc_t | None = None,
        dt_s: PositiveFloat = TIMESTEP_s_DEFAULT,
        *,
        optimize_clamp: bool = True,
    ) -> None:
        self.dt_s = dt_s  # not used in step, just for simulator
        self.cfg = StoragePRUConfig.from_vstorage(cfg, dt_s, optimize_clamp=optimize_clamp)
        self.SoC_max_1u_n32 = int(1.0 * 1e6 * 2**32)
        # state
        SoC_1u: float = 1e6 * SoC_init if SoC_init is not None else self.cfg.SoC_init_1u
        self.SoC_1u_n32 = 2**32 * SoC_1u
        self.V_OC_uV_n8 = self.lookup_V_OC_uV_n8(self.SoC_1u_n32)

    def pos_SoC(self, SoC_1u_n32: float) -> int:
        pos = int(SoC_1u_n32 / (2 ** 32) / (2 ** self.cfg.LuT_SoC_min_log2_1u))
        if pos >= LUT_SIZE:
            pos = LUT_SIZE - 1
        return pos

    def lookup_V_OC_uV_n8(self, SoC_1u_n32: float) -> float:
        return self.cfg.LuT_VOC_uV_n8[self.pos_SoC(SoC_1u_n32)]
        # TODO: high inaccuracy - log2(1M/128) = 12.93 -> round to 13

    def lookup_R_series_kOhm_n32(self, SoC_1u_n32: float) -> float:
        return self.cfg.LuT_RSeries_kOhm_n32[self.pos_SoC(SoC_1u_n32)]

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step."""
        I_charge_nA_n4 = 1e9 * 2 ** 4 * I_charge_A
        I_leak_nA_n4 = u64s(self.V_OC_uV_n8 * self.cfg.Constant_1_per_kOhm_n18 / 2 ** 22)
        # TODO: SoC_n63? 1 would be 2**63 (1 bit safety-margin to detect errors)
        # TODO:
        if I_charge_nA_n4 >= I_leak_nA_n4:
            I_delta_nA_n4 = u64s(I_charge_nA_n4 - I_leak_nA_n4)
            SoC_delta_1u_n32 = u64s(I_delta_nA_n4 * self.cfg.Constant_us_per_nAs_n40 / (2 ** 12))
            self.SoC_1u_n32 = u64s(self.SoC_1u_n32 + SoC_delta_1u_n32)

            if self.SoC_1u_n32 >= self.SoC_max_1u_n32:
                self.SoC_1u_n32 = self.SoC_max_1u_n32
        else:
            I_delta_nA_n4 = u64s(I_leak_nA_n4 - I_charge_nA_n4)
            SoC_delta_1u_n32 = u64s(I_delta_nA_n4 * self.cfg.Constant_us_per_nAs_n40 / (2 ** 12))

            if self.SoC_1u_n32 >= SoC_delta_1u_n32:
                self.SoC_1u_n32 = u64s(self.SoC_1u_n32 - SoC_delta_1u_n32)
            else:
                self.SoC_1u_n32 = 0

        self.V_OC_uV_n8 = self.lookup_V_OC_uV_n8(self.SoC_1u_n32)
        R_series_kOhm_n32 = self.lookup_R_series_kOhm_n32(self.SoC_1u_n32)

        if I_charge_nA_n4 >= 0:
            V_gain_uV_n8 = u32s(u64s(I_charge_nA_n4 * R_series_kOhm_n32) / 2 ** 28)
            V_cell_uV_n8 = u32s(self.V_OC_uV_n8 + V_gain_uV_n8)
        else:
            V_drop_uV_n8 = u32s(u64s(-I_charge_nA_n4 * R_series_kOhm_n32) / 2 ** 28)
            if self.V_OC_uV_n8 > V_drop_uV_n8:
                V_cell_uV_n8 = u32s(self.V_OC_uV_n8 - V_drop_uV_n8)
            else:
                V_cell_uV_n8 = 0

        # just for simulation
        V_OC = self.V_OC_uV_n8 / 2**8 / 1e6
        V_cell = V_cell_uV_n8 / 2**8 / 1e6
        SoC = self.SoC_1u_n32 / 2**32 / 1e6
        return V_OC, V_cell, SoC, SoC
