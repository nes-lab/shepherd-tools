"""Demonstrate behavior of Virtual Source Algorithms.

The emulation recreates an observer-cape, the virtual Source and a virtual target
- input = hdf5-file with a harvest-recording
- output = hdf5-file
- config is currently hardcoded, but it could be an emulation-task, TODO: `shepherd-data emulate config.yaml`
- target is currently a simple resistor

The output file can be analyzed and plotted with shepherds tool suite.
"""

from pathlib import Path

import numpy as np
from tqdm import tqdm

from shepherd_core import CalibrationEmulator, Reader, Writer
from shepherd_core.data_models import VirtualSourceConfig, VirtualHarvesterConfig
from shepherd_core.vsource import VirtualSourceModel

# config simulation
file_input = Path(__file__).parent.parent.parent / "hrv_ivcurve.h5"
file_output = Path(__file__).parent / "emu_ivcurve.h5"

src_list = ["BQ25570"] #"BQ25504"

#I_mcu_sleep_A = 3e-3
#I_mcu_active_A = 3e-3
R_Ohm = 1000

for vs_name in src_list:

    cal_emu = CalibrationEmulator()
    src_config = VirtualSourceConfig(
        inherit_from=vs_name,
        C_output_uF=0,
        V_output_mV=3000,
        V_intermediate_init_mV=3600,
        harvester=VirtualHarvesterConfig(name="mppt_bq_solar"),
        V_buck_drop_mV=0,
    )

    with Reader(file_input, verbose=False) as f_inp, Writer(file_output, cal_data=cal_emu, mode="emulator", verbose=False) as f_out:

        window_size = f_inp.get_window_samples()
        f_out.store_hostname("simulation")
        f_out.store_config(src_config.model_dump())
        src = VirtualSourceModel(src_config, cal_emu, log_intermediate=False, window_size=window_size)

        I_out_nA = 0

        for _t, _V_inp, _I_inp in tqdm(f_inp.read_buffers(), total=f_inp.buffers_n):

            V_out = np.empty(_V_inp.shape)
            I_out = np.empty(_I_inp.shape)

            for _iter in range(len(_t)):

                V_out_uV = src.iterate_sampling(
                    V_inp_uV=_V_inp[_iter] * 10**6,
                    I_inp_nA=_I_inp[_iter] * 10**9,
                    I_out_nA=I_out_nA,
                )
                I_out_nA = 1e3 * V_out_uV / R_Ohm

                V_out[_iter] = V_out_uV / 1e6
                I_out[_iter] = I_out_nA / 1e9

                src.cnv.get_I_mod_out_nA()

            f_out.append_iv_data_si(_t, V_out, I_out)

            # listen to power-good signal
            """
            if src.cnv.get_power_good():
                I_out_nA = int(I_mcu_active_A * 10 ** 9)
                N_good += 1
            else:
                I_out_nA = int(I_mcu_sleep_A * 10 ** 9)
            """
