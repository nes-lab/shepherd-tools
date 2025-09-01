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
from virtual_storage_config import LuT_SIZE
from virtual_storage_config import StoragePRUConfig
from virtual_storage_config import TIMESTEP_s_DEFAULT
from virtual_storage_config import VirtualStorageConfig
from virtual_storage_config import soc_t

from shepherd_core import log


class ModelStorage:
    """Abstract base class for storage models."""

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]: ...


def u32s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i >= 2**32:
        log.warning("u32-overflow")
    if i < 0:
        log.warning("u32-underflow")
    return int(min(max(i, 0), 2**32 - 1))


def u64s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i >= 2**64:
        log.warning("u64-overflow")
    if i < 0:
        log.warning("u64-underflow")
    return int(min(max(i, 0), 2**64 - 1))


class VirtualStorageModel(ModelStorage):
    """Ported python version of the pru vStorage.

    This model should behave like ModelKiBaMSimple
    """

    SoC_MAX_1_n62: int = 2**62
    LuT_SIZE_n2: int = 2**2 * LuT_SIZE

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
            cfg, TIMESTEP_s_DEFAULT, optimize_clamp=optimize_clamp
        )

        # state
        SoC_1_n30: float = 2**30 * SoC_init if SoC_init is not None else self.cfg.SoC_init_1_n30
        self.SoC_1_n62 = round(2**32 * SoC_1_n30)
        self.V_OC_uV_n8 = self.cfg.LuT_VOC_uV_n8[self.pos_LuT(self.SoC_1_n62)]

        # just for simulation
        self.steps_per_frame = round(dt_s / TIMESTEP_s_DEFAULT)

    def pos_LuT(self, SoC_1_n62: float) -> int:
        pos = u32s((SoC_1_n62 // 2**32) * self.LuT_SIZE_n2 // 2**32)
        if pos >= LuT_SIZE:
            pos = LuT_SIZE - 1
        return pos

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Slower outer step with step-size of simulation."""
        I_charge_nA_n4 = (1e9 * 2**4) * I_charge_A
        for _ in range(self.steps_per_frame - 1):
            self.step_10us(I_charge_nA_n4)
        V_cell_uV_n8 = self.step_10us(I_charge_nA_n4)
        # code below just for simulation
        V_OC = (1e-6 / 2**8) * self.V_OC_uV_n8
        V_cell = (1e-6 / 2**8) * V_cell_uV_n8
        SoC = (1 / 2**62) * self.SoC_1_n62
        return V_OC, V_cell, SoC, SoC

    def step_10us(self, I_charge_nA_n4: float) -> float:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step.

        Note: 3x u64 multiplications,
        """
        dSoC_leak_1_n62 = u64s(self.V_OC_uV_n8 * self.cfg.Constant_1_per_uV_n60 // 2**6)
        if self.SoC_1_n62 >= dSoC_leak_1_n62:
            self.SoC_1_n62 = u64s(self.SoC_1_n62 - dSoC_leak_1_n62)
        else:
            self.SoC_1_n62 = 0

        if I_charge_nA_n4 >= 0:
            dSoC_charge_1_n62 = u64s(I_charge_nA_n4 * self.cfg.Constant_1_per_nA_n60 // (2**2))
            self.SoC_1_n62 = u64s(self.SoC_1_n62 + dSoC_charge_1_n62)
            self.SoC_1_n62 = min(self.SoC_MAX_1_n62, self.SoC_1_n62)
        else:
            dSoC_discharge_1_n62 = u64s(-I_charge_nA_n4 * self.cfg.Constant_1_per_nA_n60 // (2**2))
            if self.SoC_1_n62 > dSoC_discharge_1_n62:
                self.SoC_1_n62 = u64s(self.SoC_1_n62 - dSoC_discharge_1_n62)
            else:
                self.SoC_1_n62 = 0

        pos_LuT = self.pos_LuT(self.SoC_1_n62)
        self.V_OC_uV_n8 = self.cfg.LuT_VOC_uV_n8[pos_LuT]  # TODO: is interpolation possible?
        R_series_kOhm_n32 = self.cfg.LuT_RSeries_kOhm_n32[pos_LuT]

        if I_charge_nA_n4 >= 0:
            V_gain_uV_n8 = u32s(u64s(I_charge_nA_n4 * R_series_kOhm_n32) // 2**28)
            V_cell_uV_n8 = u32s(self.V_OC_uV_n8 + V_gain_uV_n8)
        else:
            V_drop_uV_n8 = u32s(u64s(-I_charge_nA_n4 * R_series_kOhm_n32) // 2**28)
            if self.V_OC_uV_n8 > V_drop_uV_n8:
                V_cell_uV_n8 = u32s(self.V_OC_uV_n8 - V_drop_uV_n8)
            else:
                V_cell_uV_n8 = 0

        return V_cell_uV_n8
