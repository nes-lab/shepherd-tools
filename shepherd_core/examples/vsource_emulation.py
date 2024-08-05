"""Demonstrate behavior of Virtual Source Algorithms.

The emulation recreates an observer-cape, the virtual Source and a virtual target
- input = hdf5-file with a harvest-recording
- output = hdf5-file
- config is currently hardcoded, but it could be an emulation-task
- target is currently a simple resistor

The output file can be analyzed and plotted with shepherds tool suite.
"""
# TODO: `shepherd-data emulate config.yaml`

from pathlib import Path

import numpy as np
from tqdm import tqdm

from shepherd_core import CalibrationEmulator
from shepherd_core import Reader
from shepherd_core import Writer
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.vsource import VirtualSourceModel

# config simulation
file_input = Path(__file__).parent.parent.parent / "hrv_opt.h5"
file_output = Path(__file__).parent / "emu_opt04.h5"

src_list = ["BQ25504"]  # "BQ25504"

I_mcu_sleep_A = 3e-3
I_mcu_active_A = 3e-3
R_Ohm = 1000

for vs_name in src_list:
    cal_emu = CalibrationEmulator()
    src_config = VirtualSourceConfig(
        inherit_from=vs_name,
        C_output_uF=0,
        # V_output_mV=3000,
        V_intermediate_init_mV=1000,
        harvester=VirtualHarvesterConfig(name="mppt_bq_solar"),
        V_buck_drop_mV=0,
        # C_intermediate_uF=100,
        V_intermediate_disable_threshold_mV=0,
        LUT_input_efficiency=[
          # <8uA  8uA   16uA  32uA  64uA  128uA 256uA 512uA 1mA   2mA   4mA   >8mA
          [0.01, 0.01, 0.02, 0.05, 0.10, 0.15, 0.15, 0.20, 0.25, 0.30, 0.30, 0.35],  # < 128 mV
          [0.10, 0.20, 0.30, 0.40, 0.50, 0.55, 0.56, 0.57, 0.58, 0.59, 0.60, 0.61],  # > 128 mV, ~200
          [0.20, 0.40, 0.50, 0.60, 0.65, 0.66, 0.67, 0.68, 0.69, 0.70, 0.71, 0.72],  # > 256 mV, ~320
          [0.35, 0.55, 0.65, 0.71, 0.73, 0.74, 0.75, 0.75, 0.76, 0.77, 0.77, 0.78],  # > 384 mV, ~450
          [0.45, 0.65, 0.70, 0.73, 0.75, 0.77, 0.78, 0.79, 0.80, 0.81, 0.81, 0.82],  # > 512 mV, ~570
          [0.50, 0.70, 0.74, 0.76, 0.78, 0.79, 0.80, 0.81, 0.82, 0.83, 0.83, 0.84],  # > 640 mV
          [0.52, 0.73, 0.76, 0.78, 0.80, 0.81, 0.82, 0.83, 0.84, 0.85, 0.85, 0.86],  # > 768 mV
          [0.53, 0.75, 0.77, 0.79, 0.81, 0.82, 0.83, 0.84, 0.85, 0.86, 0.86, 0.87],  # > 896 mV
          [0.55, 0.77, 0.78, 0.80, 0.82, 0.83, 0.85, 0.86, 0.87, 0.87, 0.87, 0.88],  # > 1024 mV
          [0.56, 0.78, 0.79, 0.81, 0.83, 0.85, 0.87, 0.88, 0.88, 0.88, 0.88, 0.89],  # > 1152 mV
          [0.58, 0.79, 0.80, 0.82, 0.84, 0.86, 0.88, 0.89, 0.89, 0.89, 0.89, 0.90],  # > 1280 mV
          [0.60, 0.80, 0.81, 0.83, 0.85, 0.87, 0.89, 0.90, 0.90, 0.90, 0.90, 0.90],  # > 1408 mV
        ]
        # input-array[12][12] depending on array[inp_voltage][log(inp_current)],
        # influence of cap-voltage is not implemented
    )

    with Reader(file_input, verbose=False) as f_inp, Writer(
        file_output, cal_data=cal_emu, mode="emulator", verbose=False
    ) as f_out:
        window_size = f_inp.get_window_samples()
        f_out.store_hostname("simulation")
        f_out.store_config(src_config.model_dump())
        src = VirtualSourceModel(
            src_config, cal_emu, log_intermediate=False, window_size=window_size
        )

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

                # TODO: src.cnv.get_I_mod_out_nA() has more internal drains

            f_out.append_iv_data_si(_t, V_out, I_out)

            # listen to power-good signal
            """
            if src.cnv.get_power_good():
                I_out_nA = int(I_mcu_active_A * 10 ** 9)
                N_good += 1
            else:
                I_out_nA = int(I_mcu_sleep_A * 10 ** 9)
            """
