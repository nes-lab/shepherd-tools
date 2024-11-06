from pathlib import Path
from typing import Optional
from typing import Union

import numpy as np
import pytest

from shepherd_core import CalibrationPair
from shepherd_core import Reader
from shepherd_core import Writer
from shepherd_core.data_models import CalibrationEmulator as CalEmu
from shepherd_core.data_models import CalibrationHarvester as CalHrv
from shepherd_core.data_models import CalibrationSeries as CalSeries
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.task import Compression


def generate_shp_file(
    store_path: Path,
    mode: Optional[str] = None,
    datatype: Optional[str] = None,
    window_samples: Optional[int] = None,
    cal_data: Union[CalSeries, CalEmu, CalHrv, None] = None,
    config: Optional[dict] = None,
    compression: Optional[Compression] = Compression.default,
    hostname: str = "unknown",
) -> Path:
    if config is None:
        config = {}
    with Writer(
        store_path,
        mode=mode,
        datatype=datatype,
        window_samples=window_samples,
        cal_data=cal_data,
        compression=compression,
        verbose=True,
    ) as file:
        file.store_hostname(hostname)
        file.store_config(config)
        duration_s = 2
        timestamps = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))
        file.append_iv_data_si(timestamps, voltages, currents)
    return store_path


@pytest.fixture
def h5_path(tmp_path: Path) -> Path:
    return tmp_path / "hrv_test.h5"


@pytest.fixture
def h5_file(h5_path: Path) -> Path:
    generate_shp_file(h5_path)
    return h5_path


def test_writer_basics(h5_path: Path) -> None:
    generate_shp_file(h5_path)
    with Reader(h5_path, verbose=True) as file:
        assert round(file.runtime_s) == 2
        assert file.get_window_samples() == 0
        assert file.get_mode() == "harvester"
        assert file.get_config() == {}
        assert file.get_datatype() == "ivsample"
        assert file.get_hostname() == "unknown"


def test_writer_compression_1(h5_path: Path) -> None:
    generate_shp_file(h5_path, compression=Compression.gzip1)


def test_writer_unique_path(h5_file: Path) -> None:
    with Writer(h5_file) as sfw:
        assert sfw.file_path != h5_path


def test_writer_faulty_mode(h5_path: Path) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        generate_shp_file(h5_path, mode="excavator", datatype="ivcurve")


def test_writer_faulty_datatype(h5_path: Path) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        generate_shp_file(h5_path, mode="emulator", datatype="ivcurve")


def test_writer_faulty_path(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        generate_shp_file(tmp_path)


def test_writer_init_cal_emu(h5_path: Path) -> None:
    vgain = 0.123
    generate_shp_file(h5_path, cal_data=CalEmu(dac_V_A=CalibrationPair(gain=vgain)))
    # dac_V_A translates to .ds_voltage, should stay untouched
    with Reader(h5_path) as sfr:
        assert sfr.ds_voltage.attrs["gain"] == vgain
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.ds_voltage.attrs["gain"] == vgain


def test_writer_init_cal_hrv(h5_path: Path) -> None:
    vgain = 0.123
    generate_shp_file(h5_path, cal_data=CalHrv(adc_V_Sense=CalibrationPair(gain=vgain)))
    # adc_V_Sense translates to .ds_voltage, should stay untouched
    with Reader(h5_path) as sfr:
        assert sfr.ds_voltage.attrs["gain"] == vgain
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.ds_voltage.attrs["gain"] == vgain


def test_writer_init_cal_series(h5_path: Path) -> None:
    vgain = 0.123
    cs = CalSeries.from_cal(CalHrv(adc_V_Sense=CalibrationPair(gain=vgain)))
    generate_shp_file(h5_path, cal_data=cs)
    # adc_V_Sense translates to .ds_voltage, should stay untouched
    with Reader(h5_path) as sfr:
        assert sfr.ds_voltage.attrs["gain"] == vgain
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.ds_voltage.attrs["gain"] == vgain


def test_writer_faulty_window(h5_path: Path) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        generate_shp_file(h5_path, mode="harvester", datatype="ivcurve")
    with pytest.raises(ValueError):  # noqa: PT011
        generate_shp_file(
            h5_path,
            mode="harvester",
            datatype="ivcurve",
            window_samples=0,
        )


def test_writer_append_raw(h5_path: Path) -> None:
    with Writer(h5_path) as sfw:
        data_nd = np.zeros((sfw.samples_per_buffer,))
        time_float = 5.5
        time_int = 3
        time_nd = 3 + data_nd
        sfw.append_iv_data_raw(time_float, data_nd, data_nd)
        sfw.append_iv_data_raw(time_int, data_nd, data_nd)
        sfw.append_iv_data_raw(time_nd, data_nd, data_nd)
        with pytest.raises(TypeError):
            sfw.append_iv_data_raw(None, data_nd, data_nd)


def test_writer_align(h5_path: Path) -> None:
    with Writer(h5_path) as sfw:
        length = int(5.5 * sfw.samples_per_buffer)
        time_nd = np.arange(0, length * sfw.sample_interval_ns, sfw.sample_interval_ns)
        data_nd = np.zeros((int(length),))
        sfw.append_iv_data_raw(time_nd, data_nd, data_nd)
    with Reader(h5_path) as sfr:
        assert sfr.ds_voltage.size < length


def test_writer_not_align(h5_path: Path) -> None:
    with Writer(h5_path) as sfw:
        length = int(5.5 * sfw.samples_per_buffer)
        sample_interval = 10 * sfw.sample_interval_ns
        time_nd = np.arange(0, length * sample_interval, sample_interval)
        data_nd = np.zeros((int(length),))
        sfw.append_iv_data_raw(time_nd, data_nd, data_nd)
    with Reader(h5_path) as sfr:
        assert sfr.ds_voltage.size == length


def test_writer_setter(h5_path: Path) -> None:
    name = "pingu"
    with Writer(h5_path) as sfw:
        sfw["hostname"] = name
    with Reader(h5_path) as sfr:
        assert sfr.get_hostname() == name


def test_writer_modify_mode(h5_path: Path) -> None:
    generate_shp_file(h5_path, mode="harvester")
    with Reader(h5_path) as sfr:
        assert sfr.get_mode() == "harvester"
    with Writer(h5_path, modify_existing=True, mode="emulator") as sfw:
        assert sfw.get_mode() == "emulator"
    with Reader(h5_path) as sfr:
        assert sfr.get_mode() == "emulator"


def test_writer_not_modify_mode(h5_path: Path) -> None:
    generate_shp_file(h5_path, mode="harvester")
    with Reader(h5_path) as sfr:
        assert sfr.get_mode() == "harvester"
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.get_mode() == "harvester"
    with Reader(h5_path) as sfr:
        assert sfr.get_mode() == "harvester"


def test_writer_modify_datatype(h5_path: Path) -> None:
    generate_shp_file(h5_path, datatype="ivcurve", window_samples=1024)
    with Reader(h5_path) as sfr:
        assert sfr.get_datatype() == EnergyDType.ivcurve
    with Writer(h5_path, modify_existing=True, datatype="ivsample") as sfw:
        # should not be possible, but who am I?
        assert sfw.get_datatype() == EnergyDType.ivsample
    with Reader(h5_path) as sfr:
        assert sfr.get_datatype() == EnergyDType.ivsample


def test_writer_not_modify_datatype(h5_path: Path) -> None:
    generate_shp_file(h5_path, datatype="ivcurve", window_samples=1024)
    with Reader(h5_path) as sfr:
        assert sfr.get_datatype() == EnergyDType.ivcurve
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.get_datatype() == EnergyDType.ivcurve
    with Reader(h5_path) as sfr:
        assert sfr.get_datatype() == EnergyDType.ivcurve


def test_writer_modify_window_samples(h5_path: Path) -> None:
    generate_shp_file(h5_path, window_samples=1024)
    with Reader(h5_path) as sfr:
        assert sfr.get_window_samples() == 1024
    with Writer(h5_path, modify_existing=True, window_samples=2048) as sfw:
        # should not be possible, but who am I?
        assert sfw.get_window_samples() == 2048
    with Reader(h5_path) as sfr:
        assert sfr.get_window_samples() == 2048


def test_writer_not_modify_window_samples(h5_path: Path) -> None:
    generate_shp_file(h5_path, window_samples=1024)
    with Reader(h5_path) as sfr:
        assert sfr.get_window_samples() == 1024
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.get_window_samples() == 1024
    with Reader(h5_path) as sfr:
        assert sfr.get_window_samples() == 1024


def test_writer_modify_cal_data(h5_path: Path) -> None:
    cal1 = CalSeries.from_cal(CalHrv(adc_V_Sense=CalibrationPair(gain=1.23)))
    cal2 = CalSeries.from_cal(CalHrv(adc_V_Sense=CalibrationPair(gain=2.34)))
    generate_shp_file(h5_path, cal_data=cal1)
    with Reader(h5_path) as sfr:
        assert sfr.get_calibration_data().voltage.gain == 1.23
    with Writer(h5_path, modify_existing=True, cal_data=cal2) as sfw:
        assert sfw.get_calibration_data().voltage.gain == 2.34
    with Reader(h5_path) as sfr:
        assert sfr.get_calibration_data().voltage.gain == 2.34


def test_writer_not_modify_cal_data(h5_path: Path) -> None:
    cal1 = CalSeries.from_cal(CalHrv(adc_V_Sense=CalibrationPair(gain=1.23)))
    generate_shp_file(h5_path, cal_data=cal1)
    with Reader(h5_path) as sfr:
        assert sfr.get_calibration_data().voltage.gain == 1.23
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.get_calibration_data().voltage.gain == 1.23
    with Reader(h5_path) as sfr:
        assert sfr.get_calibration_data().voltage.gain == 1.23


def test_writer_modify_hostname(h5_path: Path) -> None:
    generate_shp_file(h5_path, hostname="bubu")
    with Reader(h5_path) as sfr:
        assert sfr.get_hostname() == "bubu"
    with Writer(h5_path, modify_existing=True) as sfw:
        sfw.store_hostname("sheep")
        assert sfw.get_hostname() == "sheep"
    with Reader(h5_path) as sfr:
        assert sfr.get_hostname() == "sheep"


def test_writer_not_modify_hostname(h5_path: Path) -> None:
    generate_shp_file(h5_path, hostname="bubu")
    with Reader(h5_path) as sfr:
        assert sfr.get_hostname() == "bubu"
    with Writer(h5_path, modify_existing=True) as sfw:
        assert sfw.get_hostname() == "bubu"
    with Reader(h5_path) as sfr:
        assert sfr.get_hostname() == "bubu"


# TODO: get_config

# TODO:
#  - test writing different and confirming them
#  - different compressions and their size relative to each other
#  - also invalid
#  - read raw-data
