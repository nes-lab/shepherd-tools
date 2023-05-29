""" Demonstrate behavior of Virtual Harvester Algorithms

- simulation is based on ivsamples derived from a jogging-recording


- different
    - virtual sources
    - simulation durations
    - harvesting voltages
- harvesting has a duty cycle (steps visible in plot)
- MCU switches between active/sleep depending on power-good-signal
- results are plotted

"""
from pathlib import Path

from shepherd_core import BaseReader
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import VirtualHarvester
from shepherd_core.data_models.content.virtual_harvester import HarvesterPRUConfig
from shepherd_core.vsource import VirtualHarvesterModel
from shepherd_data import ivonne

# config simulation
sim_duration = 32
file_ivonne = (
    Path(__file__).parent.parent.parent / "shepherd_data/examples/jogging_10m.iv"
)
file_ivcurve = Path(__file__).parent / "jogging_ivcurve.h5"

hrv_list = [
    "cv10",
    "mppt_voc",
    "mppt_bq_solar",  # bq needs 16 s to start -> bad performance
    "mppt_bq_thermoelectric",
    "mppt_po",
    "mppt_opt",
]

if not file_ivcurve.exists():
    with ivonne.Reader(file_ivonne) as db:
        db.convert_2_ivcurves(file_ivcurve, duration_s=sim_duration)


with BaseReader(file_ivcurve, verbose=False) as file:
    window_size = file.get_window_samples()
    I_in_max = 0.0
    for _t, _v, _i in file.read_buffers():
        I_in_max = max(I_in_max, _i.max())
    print(
        f"Input-file: \n"
        f"\tE_in = {file.energy() * 1e3:.3f} mWs\n"
        f"\tI_in_max = {I_in_max * 1e3:.3f} mA\n"
        f"\twindow_size = {window_size} n\n",
    )


for hrv_name in hrv_list:
    E_out_Ws = 0.0
    with BaseReader(file_ivcurve, verbose=False) as file:
        window_size = file.get_window_samples()
        hrv_config = VirtualHarvester(name=hrv_name)
        hrv_pru = HarvesterPRUConfig.from_vhrv(
            hrv_config,
            for_emu=True,
            dtype_in=EnergyDType.ivcurve,
            window_size=window_size,
        )
        hrv = VirtualHarvesterModel(hrv_pru)
        for _t, _v, _i in file.read_buffers():
            length = max(_v.size, _i.size)
            for _n in range(length):
                _v[_n], _i[_n] = hrv.ivcurve_sample(
                    _voltage_uV=_v[_n] * 10**6, _current_nA=_i[_n] * 10**9
                )
            E_out_Ws += (_v * _i).sum() * 1e-15 * file.sample_interval_s

        print(f"E_out = {E_out_Ws * 1e3:.3f} mWs -> {hrv_name}")
