from pathlib import Path

import pytest

from shepherd_core import BaseReader
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import VirtualHarvester
from shepherd_core.data_models.content.virtual_harvester import HarvesterPRUConfig
from shepherd_core.vsource import VirtualHarvesterModel

hrv_list = [
    "ivcurve",
    "iv1000",
    "isc_voc",
    "cv20",
    "mppt_voc",
    "mppt_bq",
    "mppt_bq_solar",
    "mppt_po",
    "mppt_opt",
]


@pytest.mark.parametrize("hrv_name", hrv_list)
def test_vsource_hrv_min(hrv_name: str) -> None:
    hrv_config = VirtualHarvester(name=hrv_name)
    hrv_pru = HarvesterPRUConfig.from_vhrv(hrv_config)
    _ = VirtualHarvesterModel(hrv_pru)


def test_vsource_hrv_create_file(file_ivcurve: Path) -> None:
    pass


@pytest.mark.parametrize("hrv_name", hrv_list[:3])
def test_vsource_hrv_fail(hrv_name: str) -> None:
    with pytest.raises(ValueError):
        hrv_config = VirtualHarvester(name=hrv_name, window_duration_n=1024)
        hrv_pru = HarvesterPRUConfig.from_vhrv(
            hrv_config, for_emu=True, dtype_inp=EnergyDType.ivcurve
        )
        _ = VirtualHarvesterModel(hrv_pru)


@pytest.mark.parametrize("hrv_name", hrv_list[3:])
def test_vsource_hrv_sim(hrv_name: str, file_ivcurve: Path) -> None:
    with BaseReader(file_ivcurve) as file:
        window_size = file.get_window_samples()
        hrv_config = VirtualHarvester(name=hrv_name, window_duration_n=window_size)
        hrv_pru = HarvesterPRUConfig.from_vhrv(
            hrv_config, for_emu=True, dtype_inp=EnergyDType.ivcurve
        )
        hrv = VirtualHarvesterModel(hrv_pru)
        for _t, _v, _i in file.read_buffers():
            length = max(_v.size, _i.size)
            for _n in range(length):
                hrv.iv_sample(
                    _voltage_uV=_v[_n] * 10**6, _current_nA=_i[_n] * 10**9
                )
