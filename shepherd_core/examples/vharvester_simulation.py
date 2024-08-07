"""Demonstrate behavior of Virtual Harvester Algorithms.

- simulation is based on ivsamples derived from a solar-isc-voc-recording during a jogging-trip
- harvesting is done by various algorithms and preconfigured virtual harvesters
- results are printed on console (harvested energy)

"""

from contextlib import ExitStack
from pathlib import Path

from shepherd_core import CalibrationHarvester
from shepherd_core import Reader
from shepherd_core import Writer
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models.content.virtual_harvester import HarvesterPRUConfig
from shepherd_core.vsource import VirtualHarvesterModel
from shepherd_data import ivonne

# config simulation
sim_duration = 32
file_ivonne = Path(__file__).parent.parent.parent / "shepherd_data/examples/jogging_10m.iv"
file_ivcurve = Path(__file__).parent / "jogging_ivcurve.h5"

hrv_list = [
    "cv20",
    # ⤷ fails due to lower solar voltage
    "cv10",
    "mppt_voc",
    "mppt_bq_solar",
    # ⤷ bq needs 16 s to start -> bad performance for this demo
    "mppt_bq_thermoelectric",
    # ⤷ thermoelectric setpoint -> bad performance for solar
    "mppt_po",
    "mppt_opt",
]

save_files: bool = True

# convert IVonne to IVCurve
if not file_ivcurve.exists():
    with ivonne.Reader(file_ivonne) as db:
        db.convert_2_ivcurves(file_ivcurve, duration_s=sim_duration)

# Input Statistics
with Reader(file_ivcurve, verbose=False) as file:
    window_size = file.get_window_samples()
    I_in_max = 0.0
    for _t, _v, _i in file.read_buffers():
        I_in_max = max(I_in_max, _i.max())
    print(
        f"Input-file: \n"
        f"\tE_in = {file.energy() * 1e3:.3f} mWs (not representative)\n"
        f"\tI_in_max = {I_in_max * 1e3:.3f} mA\n"
        f"\twindow_size = {window_size} n\n",
    )

# Simulation
for hrv_name in hrv_list:
    E_out_Ws = 0.0
    _cal = CalibrationHarvester()
    if save_files:
        stack = ExitStack()
        file_output = file_ivcurve.with_name(
            file_ivcurve.stem + "_" + hrv_name + file_ivcurve.suffix
        )
        fh_output = Writer(
            file_output, cal_data=_cal, mode="harvester", verbose=False, force_overwrite=True
        )
        stack.enter_context(fh_output)
        fh_output.store_hostname("hrv_sim_" + hrv_name)

    with Reader(file_ivcurve, verbose=False) as file:
        hrv_config = VirtualHarvesterConfig(name=hrv_name)
        hrv_pru = HarvesterPRUConfig.from_vhrv(
            hrv_config,
            for_emu=True,
            dtype_in=file.get_datatype(),
            window_size=4 * file.get_window_samples(),
        )
        hrv = VirtualHarvesterModel(hrv_pru)
        for _t, _v, _i in file.read_buffers():
            # TODO: _t should be handed to new file without conversions
            length = max(_v.size, _i.size)
            for _n in range(length):
                _v[_n], _i[_n] = hrv.ivcurve_sample(
                    _voltage_uV=_v[_n] * 10**6, _current_nA=_i[_n] * 10**9
                )
            E_out_Ws += (_v * _i).sum() * 1e-15 * file.sample_interval_s
            if save_files:
                fh_output.append_iv_data_si(_t, _v / 1e6, _i / 1e9)
        if save_files:
            stack.close()
            with Reader(file_output) as fh_output:
                fh_output.save_metadata()
        print(f"E_out = {E_out_Ws * 1e3:.3f} mWs -> {hrv_name}")
