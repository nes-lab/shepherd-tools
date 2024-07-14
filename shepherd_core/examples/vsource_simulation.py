"""Demonstrate behavior of Virtual Source Algorithms.

- simulation combines a range of
    - virtual sources
    - simulation durations
    - harvesting voltages
- harvesting has a duty cycle (steps visible in plot)
- MCU switches between active/sleep depending on power-good-signal
- results are plotted

"""

from itertools import product

import matplotlib.pyplot as plt
import numpy as np

from shepherd_core import CalibrationEmulator
from shepherd_core import WebClient
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.vsource import VirtualSourceModel

# config simulation
sample_dur_list = [50_000, 500_000]
v_hrv_mV_list = [1200, 3300]
charge_rate = 0.5

src_list = [
    "direct",
    "diode+capacitor",
    "diode+resistor+capacitor",
    "BQ25504",
    "BQ25504s",
    "BQ25570",
    "BQ25570s",
]

I_mcu_sleep_A = 200e-9
I_mcu_active_A = 1e-3

# For online-queries the lib can be connected to the testbed-server.
# NOTE: there are 3 states:
# - unconnected -> demo-fixtures are queried (locally)
# - connected -> publicly available data is queried online
# - logged in with valid token -> also private data is queried online
do_connect = False
if do_connect:
    WebClient()

for vs_name, v_hrv_mV, samples in product(src_list, v_hrv_mV_list, sample_dur_list):
    # prepare simulation
    ts = np.arange(0, samples * 10e-6, 10e-6)
    vcaps = np.empty((samples, 3))

    src_config = VirtualSourceConfig(name=vs_name)
    cal_emu = CalibrationEmulator()
    src = VirtualSourceModel(src_config, cal_emu, log_intermediate=True)

    I_out_nA = int(I_mcu_sleep_A * 10**9)
    N_good = 0
    for i in range(samples):
        # Harvest at 100uA
        if (i % 1_000) < charge_rate * 1_000:
            V_out_uV = src.iterate_sampling(
                V_inp_uV=v_hrv_mV * 10**3,
                I_inp_nA=100_000,
                I_out_nA=I_out_nA,
            )
        else:
            V_out_uV = src.iterate_sampling(I_out_nA=I_out_nA)

        # listen to power-good signal
        if src.cnv.get_power_good():
            I_out_nA = int(I_mcu_active_A * 10**9)
            N_good += 1
        else:
            I_out_nA = int(I_mcu_sleep_A * 10**9)

        # store sim-results
        vcaps[i] = [
            src.cnv.get_V_intermediate_uV() * 1e-6,
            V_out_uV * 1e-6,
            src.cnv.get_power_good(),
        ]

    # visualize results
    pwr_good_ratio = round(100 * N_good / samples, 3)
    t_s = samples // 100
    print(f"Power-Good-Ratio = {pwr_good_ratio} % (for {vs_name}, {v_hrv_mV} mV, {t_s} ms)")

    fig = plt.figure(figsize=(20, 8))
    plt.plot(ts, vcaps)
    plt.suptitle(
        f"VSrc-Simulation [{vs_name}, V_inp={v_hrv_mV}mV, "
        f"duty={charge_rate}, duration={t_s}ms] "
        f"-> pwr-good-ratio={pwr_good_ratio} %"
    )
    plt.xlabel("Runtime [s]")
    plt.ylabel("Voltages [V]")
    plt.legend(["V_Cap", "V_Out", "PGood"], loc="upper right")
    plt.tight_layout()
    plt.savefig(f"./vsource_sim_{vs_name}_{v_hrv_mV}mV_{t_s}ms.png")
    plt.close(fig)
