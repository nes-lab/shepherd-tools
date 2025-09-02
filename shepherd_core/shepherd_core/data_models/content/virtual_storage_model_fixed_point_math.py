"""Playground to determine the best integer-math and fit constants."""

from itertools import product

from shepherd_core import log
from shepherd_core.data_models.content.virtual_storage_config import LuT_SIZE_LOG


def u32l(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i >= 2**32:
        log.warning("u32-overflow (%d)", i)
    if i < 0:
        log.warning("u32-underflow (%d)", i)
    return round(min(max(i, 0), 2**32 - 1))


# #### I_charge-to-dSoC #####
# Goal: Allow ~1 uF Capacitor to 800 mAh battery

dt_s = 10e-6
qs_As = [1e-6 * 1 * 2.0, 1e-6 * 5 * 2.5, 1e-6 * 10 * 3.6, 800 * 3.6]
Constant_1u_per_nA_n40 = [u32l((2**40 / 1e3) * dt_s / q_As) for q_As in qs_As]
Constant_1_per_nA_n60 = [u32l((2**60 / 1e9) * dt_s / q_As) for q_As in qs_As]

# #### SoC-to-position #####
# Goal: As-simple-as-possible

SoCs_1u_n32 = [round(x / 10 * 1e6 * 2**32) for x in range(11)]
LUT_SIZE = 128

# First Approach (1 Division in pos-calc -> impossible for PRU)
SoC_min_1u = round(1e6 / LUT_SIZE)
positions1 = [int(SoC_1u_n32 / SoC_min_1u / 2**32) for SoC_1u_n32 in SoCs_1u_n32]

# Second Approach
SoC_min = 1.0 / LUT_SIZE
inv_SoC_min_1M_n32 = round(2**32 / 1e6 / SoC_min)  # 1M / SoC_min
positions2 = [
    int(int(SoC_1u_n32 / 2**32) * inv_SoC_min_1M_n32 / 2**32) for SoC_1u_n32 in SoCs_1u_n32
]

# third approach
SoCs_1_n62 = [round(x / 10 * 2**62) for x in range(11)]
positions3 = [int(int(SoC_1_n62 / 2**32) * LUT_SIZE / 2**30) for SoC_1_n62 in SoCs_1_n62]

# final approach (upper u32 & rest of shift)
positions4 = [u32l(SoC_1_n62 // 2 ** (62 - LuT_SIZE_LOG)) for SoC_1_n62 in SoCs_1_n62]

# #### R_Leak-to-dSoC #####
# Goal: biggest possible dynamic range

Rs_leak_Ohm = [1e3, 10e3, 100e3, 1e6, 10e6]
Constants_1_per_V = [dt_s / q_As / R_leak_Ohm for q_As, R_leak_Ohm in product(qs_As, Rs_leak_Ohm)]
Constants_1u_per_uV_n40 = [u32l((2**40) * c_1_per_V) for c_1_per_V in Constants_1_per_V]
Constants_1_per_uV_n60 = [u32l((2**60 / 1e6) * c_1_per_V) for c_1_per_V in Constants_1_per_V]

print("done")  # noqa: T201
