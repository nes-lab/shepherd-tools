"""Demonstrate behavior of Virtual Source Algorithms.

The emulation recreates an observer-cape, the virtual Source and a virtual target
- input = hdf5-file with a harvest-recording
- output = hdf5-file
- config is currently hardcoded, but it could be an emulation-task
- target is currently a simple resistor

The output file can be analyzed and plotted with shepherds tool suite.

Output:
E_out = 0.007 mWs -> direct
E_out = 0.033 mWs -> diode+capacitor
E_out = 0.033 mWs -> diode+resistor+capacitor
E_out = 14.964 mWs -> BQ25504
E_out = 15.042 mWs -> BQ25504s
E_out = 13.909 mWs -> BQ25570
E_out = 14.073 mWs -> BQ25570s
"""

from pathlib import Path

from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.vsource import ConstantCurrentTarget
from shepherd_core.vsource import simulate_source

# config simulation
file_input = Path(__file__).parent / "jogging_ivcurve.h5"

src_list = [
    "direct",
    "diode+capacitor",
    "diode+resistor+capacitor",
    "BQ25504",
    "BQ25504s",
    "BQ25570",
    "BQ25570s",
]
tgt = ConstantCurrentTarget(i_active_A=1e-3, i_sleep_A=200e-9)
save_files = False

for src_name in src_list:
    file_output = (
        file_input.with_name(file_input.stem + "_emu_" + src_name + file_input.suffix)
        if save_files
        else None
    )

    e_out_Ws = simulate_source(
        config=VirtualSourceConfig(name=src_name),
        target=tgt,
        path_input=file_input,
        path_output=file_output,
    )
    print(f"E_out = {e_out_Ws * 1e3:.3f} mWs -> {src_name}")
