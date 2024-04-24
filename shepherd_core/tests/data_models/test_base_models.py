import os
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from shepherd_core.data_models.base.cal_measurement import CalMeasurementCape
from shepherd_core.data_models.base.calibration import CalibrationCape
from shepherd_core.data_models.base.calibration import CalibrationEmulator
from shepherd_core.data_models.base.calibration import CalibrationHarvester
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.base.calibration import CapeData
from shepherd_core.data_models.base.content import ContentModel


def test_base_model_cape_data() -> None:
    CapeData(serial_number="xyz1")


def test_base_model_cape_data_fail() -> None:
    with pytest.raises(ValidationError):
        CapeData()


def test_base_model_cal_pair_conv() -> None:
    cal = CalibrationPair(gain=4.9)
    val_raw = 500
    val_si = cal.raw_to_si(val_raw)
    val_rbw = cal.si_to_raw(val_si)
    assert val_raw == val_rbw


def test_base_model_cal_pair_conv2() -> None:
    cal = CalibrationPair(gain=44)
    rng = np.random.default_rng()
    val_raw = rng.integers(low=0, high=2000, size=20)
    val_si = cal.raw_to_si(val_raw)
    val_rbw = cal.si_to_raw(val_si)
    assert val_raw.size == val_rbw.size


def test_base_model_cal_series_min() -> None:
    CalibrationSeries()


def test_base_model_cal_series_all() -> None:
    cal = CalibrationCape()
    _ = CalibrationSeries.from_cal(cal.harvester)
    _ = CalibrationSeries.from_cal(cal.emulator)
    _ = CalibrationSeries.from_cal(cal.emulator, emu_port_a=True)
    _ = CalibrationSeries.from_cal(cal.emulator, emu_port_a=False)


def test_base_model_cal_hrv_min() -> None:
    cal = CalibrationHarvester()
    cs = cal.export_for_sysfs()
    assert len(cs) == 6


def test_base_model_cal_emu_min() -> None:
    cal = CalibrationEmulator()
    cs = cal.export_for_sysfs()
    assert len(cs) == 6


def test_base_model_cal_cape_bytestr() -> None:
    cal1 = CalibrationCape()
    cb = cal1.to_bytestr()
    cal2 = CalibrationCape.from_bytestr(cb)
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_cape_bytestr_with_cape_data() -> None:
    cal1 = CalibrationCape(cape=CapeData(serial_number="123"))
    cb = cal1.to_bytestr()
    cal2 = CalibrationCape.from_bytestr(cb, cal1.cape)
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_cape_example(tmp_path: Path) -> None:
    cal0 = CalMeasurementCape()
    path1 = Path(__file__).resolve().with_name("example_cal_data.yaml")
    cal1 = CalibrationCape.from_file(path1)
    path2 = tmp_path / "cal_data_new.yaml"
    cal1.to_file(path2)
    cal2 = CalibrationCape.from_file(path2)
    assert cal0.get_hash() != cal1.get_hash()
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_hrv_fault() -> None:
    path = Path(__file__).resolve().with_name("example_cal_data_faulty.yaml")
    cal = CalibrationCape.from_file(path)
    with pytest.raises(ValueError):  # noqa: PT011
        _ = cal.harvester.export_for_sysfs()


def test_base_model_cal_emu_fault() -> None:
    path = Path(__file__).resolve().with_name("example_cal_data_faulty.yaml")
    cal = CalibrationCape.from_file(path)
    with pytest.raises(ValueError):  # noqa: PT011
        _ = cal.emulator.export_for_sysfs()


def test_base_model_cal_meas_min() -> None:
    cm1 = CalMeasurementCape()
    cal1 = cm1.to_cal()
    cal2 = CalibrationCape()
    assert cal1.get_hash() == cal2.get_hash()


def test_base_model_cal_meas_example() -> None:
    path1 = Path(__file__).resolve().with_name("example_cal_meas.yaml")
    cm1 = CalMeasurementCape.from_file(path1)
    cal1 = cm1.to_cal()
    cal2 = CalibrationCape()
    assert cal1.get_hash() != cal2.get_hash()


def test_base_model_cal_meas_fault_correlation() -> None:
    path = Path(__file__).resolve().with_name("example_cal_meas_faulty1.yaml")
    with pytest.raises(ValidationError):
        _ = CalMeasurementCape.from_file(path)


def test_base_model_cal_meas_fault_no_pairs() -> None:
    path = Path(__file__).resolve().with_name("example_cal_meas_faulty2.yaml")
    with pytest.raises(ValidationError):
        _ = CalMeasurementCape.from_file(path)


def test_base_model_content_str_repr() -> None:
    content = ContentModel(name="tricky", owner="peter", group="work")
    print(content)
    assert str(content) == "tricky"


def test_base_model_content_public_group() -> None:
    _ = ContentModel(
        name="tricky",
        description="fake",
        owner="peter",
        group="work",
        visible2group=True,
    )
    with pytest.raises(ValidationError):
        _ = ContentModel(name="tricky", owner="peter", group="work", visible2group=True)


def test_base_model_content_public_all() -> None:
    _ = ContentModel(
        name="tricky", description="fake", owner="peter", group="work", visible2all=True
    )
    with pytest.raises(ValidationError):
        _ = ContentModel(name="tricky", owner="peter", group="work", visible2all=True)


# ContentModel below is used as inheritor of ShpModel


def test_base_model_shepherd_scheme(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    ContentModel.schema_to_file(tmp_path / "schema.yaml")


def test_base_model_shepherd_min(tmp_path: Path) -> None:
    content = ContentModel(name="tricky", owner="peter", group="work")
    content.to_file(tmp_path / "content1.yaml", minimal=True)
    content.to_file(tmp_path / "content2.yaml", minimal=False)
    # minimal should produce min-set (input dict), but does not work currently


def test_base_model_shepherd_fault_load_other(tmp_path: Path) -> None:
    path = tmp_path / "content.yaml"
    content = ContentModel(name="tricky", owner="peter", group="work")
    content.to_file(path)
    with pytest.raises(ValueError):  # noqa: PT011
        CalibrationCape.from_file(path)


def test_base_model_shepherd_fault_mutation() -> None:
    content = ContentModel(name="tricky", owner="peter", group="work")
    with pytest.raises(ValidationError):
        content.name = "whatever"


def test_base_model_shepherd_fault_short_str() -> None:
    with pytest.raises(ValidationError):
        _ = ContentModel(name="", owner="peter", group="work")


def test_base_model_shepherd_fault_long_str() -> None:
    with pytest.raises(ValidationError):
        _ = ContentModel(
            name="very_long_123456789_123456789_1234567890", owner="peter", group="work"
        )


def test_base_model_shepherd_fault_unsafe_str() -> None:
    with pytest.raises(ValidationError):
        _ = ContentModel(name="fs_trouble<>", owner="peter", group="work")
    with pytest.raises(ValidationError):
        _ = ContentModel(name="unicode", owner="peter", group="work", description="🐍")
