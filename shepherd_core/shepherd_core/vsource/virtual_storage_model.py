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

from shepherd_core import log
from shepherd_core.data_models.content.virtual_storage_config import LuT_SIZE
from shepherd_core.data_models.content.virtual_storage_config import LuT_SIZE_LOG
from shepherd_core.data_models.content.virtual_storage_config import StoragePRUConfig
from shepherd_core.data_models.content.virtual_storage_config import TIMESTEP_s_DEFAULT
from shepherd_core.data_models.content.virtual_storage_config import VirtualStorageConfig
from shepherd_core.data_models.content.virtual_storage_config import soc_t


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


class VirtualStorageModelPRU:
    """Ported python version of the pru vStorage.

    This model should behave like ModelKiBaMSimple
    """

    SoC_MAX_1_n62: int = 2**62 - 1
    SoC_TO_POS_DIV: int = 2 ** (62 - LuT_SIZE_LOG)

    @validate_call
    def __init__(
        self,
        cfg: StoragePRUConfig,
        SoC_init: soc_t | None = None,
    ) -> None:
        self.cfg_pru = cfg
        # state
        SoC_1_n30: float = 2**30 * SoC_init if SoC_init is not None else self.cfg_pru.SoC_init_1_n30
        self.SoC_1_n62 = round(2**32 * SoC_1_n30)
        self.V_OC_uV_n8 = self.cfg_pru.LuT_VOC_uV_n8[self.pos_LuT(self.SoC_1_n62)]

    def pos_LuT(self, SoC_1_n62: int) -> int:
        pos = u32s(SoC_1_n62 // self.SoC_TO_POS_DIV)
        if pos >= LuT_SIZE:
            pos = LuT_SIZE - 1
        return pos

    def calc_V_OC_uV(self) -> int:
        pos_LuT = self.pos_LuT(self.SoC_1_n62)
        return round(self.cfg_pru.LuT_VOC_uV_n8[pos_LuT] // 2**8)

    def step(self, I_delta_nA_n4: float, *, is_charging: bool) -> float:
        """Calculate the battery SoC & cell-voltage after drawing a current over a time-step.

        Note: 3x u64 multiplications
        """
        dSoC_leak_1_n62 = u64s((self.V_OC_uV_n8 // 2**6) * self.cfg_pru.Constant_1_per_uV_n60)
        if self.SoC_1_n62 >= dSoC_leak_1_n62:
            self.SoC_1_n62 = u64s(self.SoC_1_n62 - dSoC_leak_1_n62)
        else:
            self.SoC_1_n62 = 0

        dSoC_1_n62 = u64s(I_delta_nA_n4 * self.cfg_pru.Constant_1_per_nA_n60 // (2**2))
        if is_charging:
            self.SoC_1_n62 = u64s(self.SoC_1_n62 + dSoC_1_n62)
            self.SoC_1_n62 = min(self.SoC_MAX_1_n62, self.SoC_1_n62)
        elif self.SoC_1_n62 > dSoC_1_n62:
            self.SoC_1_n62 = u64s(self.SoC_1_n62 - dSoC_1_n62)
        else:
            self.SoC_1_n62 = 0

        pos_LuT = self.pos_LuT(self.SoC_1_n62)
        self.V_OC_uV_n8 = self.cfg_pru.LuT_VOC_uV_n8[pos_LuT]
        # TODO: is interpolation possible?
        R_series_kOhm_n32 = self.cfg_pru.LuT_RSeries_kOhm_n32[pos_LuT]
        V_delta_uV_n8 = u32s(u64s(I_delta_nA_n4 * R_series_kOhm_n32) // 2**28)

        if is_charging:
            V_cell_uV_n8 = u32s(self.V_OC_uV_n8 + V_delta_uV_n8)
        elif self.V_OC_uV_n8 > V_delta_uV_n8:
            V_cell_uV_n8 = u32s(self.V_OC_uV_n8 - V_delta_uV_n8)
        else:
            V_cell_uV_n8 = 0

        if self.SoC_1_n62 == 0:
            return 0  # cell voltage breaks down
        return V_cell_uV_n8 // 2**8  # u32 uV


class VirtualStorageModel(VirtualStorageModelPRU, ModelStorage):
    """Higher level Model that can run on a coarser timebase.

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
        # metadata for simulator
        self.cfg: VirtualStorageConfig = cfg
        self.dt_s = dt_s
        # prepare PRU-Model
        cfg_pru = StoragePRUConfig.from_vstorage(
            cfg, TIMESTEP_s_DEFAULT, optimize_clamp=optimize_clamp
        )
        super().__init__(cfg_pru, SoC_init=SoC_init)

        # just for simulation
        self.steps_per_frame = round(dt_s / TIMESTEP_s_DEFAULT)

    def step(self, I_charge_A: float) -> tuple[float, float, float, float]:
        """Slower outer step with step-size of simulation."""
        I_delta_nA_n4 = abs(2**4 * (1e9 * I_charge_A))
        is_charging = I_charge_A >= 0
        for _ in range(self.steps_per_frame - 1):
            super().step(I_delta_nA_n4, is_charging=is_charging)
        V_cell_uV = super().step(I_delta_nA_n4, is_charging=is_charging)
        # code below just for simulation
        V_OC = (1e-6 / 2**8) * self.V_OC_uV_n8
        V_cell = 1e-6 * V_cell_uV
        SoC = (1 / 2**62) * self.SoC_1_n62
        return V_OC, V_cell, SoC, SoC
