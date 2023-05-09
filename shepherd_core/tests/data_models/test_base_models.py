from pathlib import Path

import numpy as np

from shepherd_core.data_models.base.cal_measurement import CalMeasurementCape
from shepherd_core.data_models.base.calibration import CalibrationCape
from shepherd_core.data_models.base.calibration import CalibrationEmulator
from shepherd_core.data_models.base.calibration import CalibrationHarvester
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries


def test_base_model_cal_pair_conv():
    cal = CalibrationPair(gain=4.9)
    val_raw = 500
    val_si = cal.raw_to_si(val_raw)
    val_rbw = cal.si_to_raw(val_si)
    assert val_raw == val_rbw


def test_base_model_cal_pair_conv2():
    cal = CalibrationPair(gain=44)
    val_raw = np.random.randint(low=0, high=2000, size=20)
    val_si = cal.raw_to_si(val_raw)
    val_rbw = cal.si_to_raw(val_si)
    assert val_raw.size == val_rbw.size


def test_base_model_cal_series_min():
    CalibrationSeries()


def test_base_model_cal_hrv_min():
    cal = CalibrationHarvester()
    cs = cal.export_for_sysfs()
    assert len(cs) == 6


def test_base_model_cal_emu_min():
    cal = CalibrationEmulator()
    cs = cal.export_for_sysfs()
    assert len(cs) == 6


def test_base_model_cal_cape_bytestr():
    cal1 = CalibrationCape()
    cb = cal1.to_bytestr()
    cal2 = CalibrationCape.from_bytestr(cb)
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_cape_example(tmp_path: Path):
    cal0 = CalMeasurementCape()
    path1 = Path(__file__).absolute().with_name("example_cal_data.yaml")
    cal1 = CalibrationCape.from_file(path1)
    path2 = tmp_path / "cal_data_new.yaml"
    cal1.to_file(path2)
    cal2 = CalibrationCape.from_file(path2)
    assert cal0.get_hash() != cal1.get_hash()
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_meas_min():
    cm1 = CalMeasurementCape()
    cal1 = cm1.to_cal()
    cal2 = CalibrationCape()
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_meas_example():
    path1 = Path(__file__).absolute().with_name("example_cal_meas.yaml")
    cm1 = CalMeasurementCape.from_file(path1)
    cal1 = cm1.to_cal()
    cal2 = CalibrationCape()
    assert cal1.get_hash() != cal2.get_hash()
