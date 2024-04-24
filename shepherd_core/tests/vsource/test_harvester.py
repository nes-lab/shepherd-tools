from pathlib import Path

import pytest

from shepherd_core import Reader
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import VirtualHarvesterConfig
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
    hrv_config = VirtualHarvesterConfig(name=hrv_name)
    hrv_pru = HarvesterPRUConfig.from_vhrv(hrv_config)
    _ = VirtualHarvesterModel(hrv_pru)


def test_vsource_hrv_create_files(
    file_ivcurve: Path, file_ivsample: Path, file_isc_voc: Path
) -> None:
    pass


@pytest.mark.parametrize("hrv_name", hrv_list[:3])
def test_vsource_hrv_fail_ivcurve(hrv_name: str) -> None:
    # the first algos are not usable for ivcurve
    hrv_config = VirtualHarvesterConfig(name=hrv_name)
    with pytest.raises(ValueError):  # noqa: PT011
        _ = HarvesterPRUConfig.from_vhrv(hrv_config, for_emu=True, dtype_in=EnergyDType.ivcurve)


@pytest.mark.parametrize("hrv_name", hrv_list[3:])
def test_vsource_hrv_sim(hrv_name: str, file_ivcurve: Path) -> None:
    with Reader(file_ivcurve) as file:
        hrv_config = VirtualHarvesterConfig(name=hrv_name)
        hrv_pru = HarvesterPRUConfig.from_vhrv(
            hrv_config,
            for_emu=True,
            dtype_in=file.get_datatype(),
            window_size=file.get_window_samples(),
        )
        hrv = VirtualHarvesterModel(hrv_pru)
        for _t, _v, _i in file.read_buffers():
            length = max(_v.size, _i.size)
            for _n in range(length):
                hrv.ivcurve_sample(_voltage_uV=_v[_n] * 10**6, _current_nA=_i[_n] * 10**9)


@pytest.mark.parametrize("hrv_name", hrv_list[3:])
def test_vsource_hrv_fail_isc_voc(hrv_name: str) -> None:
    # not implemented ATM
    hrv_config = VirtualHarvesterConfig(name=hrv_name)
    with pytest.raises(NotImplementedError):
        _ = HarvesterPRUConfig.from_vhrv(hrv_config, for_emu=True, dtype_in=EnergyDType.isc_voc)


def test_vsource_hrv_fail_unknown_type() -> None:
    hrv_config = VirtualHarvesterConfig(name="mppt_voc")
    with pytest.raises(KeyError):
        _ = HarvesterPRUConfig.from_vhrv(hrv_config, for_emu=True, dtype_in="xyz")
