"""this is ported py-version of the pru-code.

Goals:

- stay close to original code-base (fixed-point integer math)
- offer a comparison for the tests
- step 1 to a virtualization of emulation

NOTE1: DO NOT OPTIMIZE -> stay close to original c-code-base

Compromises:

- Py has to map the settings-list to internal vars -> is kernel-task

Expected deviations:

- lead charge ramp maxes out early on cell-voltage (max of V_uV_n8 is 16.78 V)

"""

from pydantic import PositiveFloat
from pydantic import validate_call
from virtual_storage import LUT_SIZE
from virtual_storage import StoragePRUConfig
from virtual_storage import TIMESTEP_s_DEFAULT
from virtual_storage import VirtualStorageConfig
from virtual_storage import soc_t

from shepherd_core import log


class ModelStorage:
    """Abstract base class for storage models."""

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]: ...


def u32s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i > 2**32:
        log.warning("u32-overflow")
    if i < 0:
        log.warning("u32-underflow")
    return int(min(max(i, 0), 2**32))


def u64s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i > 2**64:
        log.warning("u64-overflow")
    if i < 0:
        log.warning("u64-underflow")
    return int(min(max(i, 0), 2**64))


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
        self.dt_s: float = dt_s  # not used in step, just for simulator
        self.cfg: StoragePRUConfig = StoragePRUConfig.from_vstorage(
            cfg, dt_s, optimize_clamp=optimize_clamp
        )
        self.SoC_max_1u_n32: int = int(1.0 * 1e6 * 2**32)
        # state
        SoC_1u: float = 1e6 * SoC_init if SoC_init is not None else self.cfg.SoC_init_1u
        self.SoC_1u_n32 = round(2**32 * SoC_1u)
        self.V_OC_uV_n8 = self.cfg.LuT_VOC_uV_n8[self.pos_LuT(self.SoC_1u_n32)]

    def pos_LuT(self, SoC_1u_n32: float) -> int:
        pos = u32s((SoC_1u_n32 / 2**32) * self.cfg.LuT_inv_SoC_min_1M_n32 / 2**32)
        if pos >= LUT_SIZE:
            pos = LUT_SIZE - 1
        return pos

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step.

        Note: 3x u64 multiplications,
        """
        I_charge_nA_n4 = 1e9 * 2**4 * I_charge_A
        I_leak_nA_n4 = u64s(self.V_OC_uV_n8 * self.cfg.Constant_1_per_kOhm_n18 / 2**22)
        # TODO: SoC_n63? 1 would be 2**63 (1 bit safety-margin to detect errors)
        # TODO: or just SoC_n32, so 1 is 0xFFFFFFFF?
        if I_charge_nA_n4 >= I_leak_nA_n4:
            I_delta_nA_n4 = u64s(I_charge_nA_n4 - I_leak_nA_n4)
            SoC_delta_1u_n32 = u64s(I_delta_nA_n4 * self.cfg.Constant_us_per_nAs_n40 / (2**12))
            self.SoC_1u_n32 = u64s(self.SoC_1u_n32 + SoC_delta_1u_n32)

            self.SoC_1u_n32 = min(self.SoC_max_1u_n32, self.SoC_1u_n32)
        else:
            I_delta_nA_n4 = u64s(I_leak_nA_n4 - I_charge_nA_n4)
            SoC_delta_1u_n32 = u64s(I_delta_nA_n4 * self.cfg.Constant_us_per_nAs_n40 / (2**12))

            if self.SoC_1u_n32 >= SoC_delta_1u_n32:
                self.SoC_1u_n32 = u64s(self.SoC_1u_n32 - SoC_delta_1u_n32)
            else:
                self.SoC_1u_n32 = 0

        pos_LuT = self.pos_LuT(self.SoC_1u_n32)
        self.V_OC_uV_n8 = self.cfg.LuT_VOC_uV_n8[pos_LuT]  # TODO: is interpolation possible?
        R_series_kOhm_n32 = self.cfg.LuT_RSeries_kOhm_n32[pos_LuT]

        if I_charge_nA_n4 >= 0:
            V_gain_uV_n8 = u32s(u64s(I_charge_nA_n4 * R_series_kOhm_n32) / 2**28)
            V_cell_uV_n8 = u32s(self.V_OC_uV_n8 + V_gain_uV_n8)
        else:
            V_drop_uV_n8 = u32s(u64s(-I_charge_nA_n4 * R_series_kOhm_n32) / 2**28)
            if self.V_OC_uV_n8 > V_drop_uV_n8:
                V_cell_uV_n8 = u32s(self.V_OC_uV_n8 - V_drop_uV_n8)
            else:
                V_cell_uV_n8 = 0

        # just for simulation
        V_OC = self.V_OC_uV_n8 / 2**8 / 1e6
        V_cell = V_cell_uV_n8 / 2**8 / 1e6
        # TODO: model matches completely, except self-discharge
        # TODO: look at delta and describe deviations
        SoC = self.SoC_1u_n32 / 2**32 / 1e6
        return V_OC, V_cell, SoC, SoC
