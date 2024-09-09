from pathlib import Path

import pytest
from pydantic import ValidationError

from shepherd_core import fw_tools
from shepherd_core.data_models.content import EnergyDType
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import FirmwareDType
from shepherd_core.data_models.content import VirtualHarvesterConfig
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.content.virtual_source import ConverterPRUConfig
from shepherd_core.data_models.testbed import MCU

from .conftest import files_elf


def test_content_model_ee_min1() -> None:
    EnergyEnvironment(
        id=9999,
        name="some",
        data_path="./file",
        data_type="isc_voc",
        duration=1,
        energy_Ws=0.1,
        owner="jane",
        group="wayne",
    )


def test_content_model_ee_min2() -> None:
    EnergyEnvironment(
        id="98765",
        name="some",
        data_path="./file",
        data_type=EnergyDType.ivcurve,
        duration=999,
        energy_Ws=3.1,
        owner="jane",
        group="wayne",
    )


def test_content_model_fw_faulty() -> None:
    with pytest.raises(ValidationError):
        Firmware(
            id=9999,
            name="dome",
            mcu=MCU(name="nRF52"),
            data="xyz",
            data_type=FirmwareDType.base64_hex,
            owner="Obelix",
            group="Gaul",
        )


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_min(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    Firmware(
        id=9999,
        name="dome",
        mcu=MCU(name="nRF52"),
        data=fw_tools.file_to_base64(path_hex),
        data_type=FirmwareDType.base64_hex,
        owner="Obelix",
        group="Gaul",
    )


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_from_elf(path_elf: Path) -> None:
    Firmware.from_firmware(
        file=path_elf,
        name="dome",
        owner="Obelix",
        group="Gaul",
    )


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_from_hex(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    Firmware.from_firmware(
        file=path_hex,
        name="dome",
        owner="Obelix",
        group="Gaul",
    )


def test_content_model_fw_from_hex_failing(tmp_path: Path) -> None:
    path_hex = tmp_path / "some.hex"
    with path_hex.open("w") as fd:
        fd.write("something")
    with pytest.raises(ValueError):  # noqa: PT011
        Firmware.from_firmware(
            file=path_hex,
            name="dome",
            owner="Obelix",
            group="Gaul",
        )


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_extract_elf_to_dir(path_elf: Path, tmp_path: Path) -> None:
    fw = Firmware.from_firmware(
        file=path_elf,
        name="dome",
        owner="Obelix",
        group="Gaul",
    )
    file = fw.extract_firmware(tmp_path)
    assert file.exists()
    assert file.is_file()


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_extract_hex_to_dir(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    fw = Firmware.from_firmware(
        file=path_hex,
        name="dome",
        owner="Obelix",
        group="Gaul",
    )
    file = fw.extract_firmware(tmp_path)
    assert file.exists()
    assert file.is_file()


@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_extract_path_elf_to_dir(path_elf: Path, tmp_path: Path) -> None:
    assert path_elf.exists()
    fw = Firmware(
        data=path_elf,
        data_type=FirmwareDType.path_elf,
        mcu={"name": "MSP430FR"},
        name="dome",
        owner="Obelix",
        group="Gaul",
    )
    file = fw.extract_firmware(tmp_path)
    assert file.exists()
    assert file.is_file()


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_content_model_fw_extract_path_hex_to_dir(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    assert path_hex.exists()
    fw = Firmware(
        data=path_hex,
        data_type=FirmwareDType.path_hex,
        mcu={"name": "MSP430FR"},
        name="dome",
        owner="Obelix",
        group="Gaul",
    )
    file = fw.extract_firmware(tmp_path)
    assert file.exists()
    assert file.is_file()


def test_content_model_hrv_min() -> None:
    hrv = VirtualHarvesterConfig(
        id=9999,
        name="whatever",
        owner="jane",
        group="wayne",
        algorithm="mppt_opt",
    )
    assert hrv.get_datatype() == "ivsample"


def test_content_model_hrv_neutral() -> None:
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="neutral")


@pytest.mark.parametrize("name", ["iv110", "cv24", "mppt_voc", "mppt_po"])
def test_content_model_hrv_by_name(name: str) -> None:
    _ = VirtualHarvesterConfig(name=name)


@pytest.mark.parametrize("uid", [1103, 1200, 2102, 2204, 2205, 2206])
def test_content_model_hrv_by_id(uid: int) -> None:
    _ = VirtualHarvesterConfig(id=uid)


def test_content_model_hrv_steps() -> None:
    hrv = VirtualHarvesterConfig(
        name="ivcurves", voltage_min_mV=1000, voltage_max_mV=4000, samples_n=11
    )
    assert hrv.voltage_step_mV == 300


def test_content_model_hrv_faulty_voltage0() -> None:
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="iv110", voltage_max_mV=5001)
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="iv110", voltage_min_mV=-1)


def test_content_model_hrv_faulty_voltage1() -> None:
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="iv110", voltage_min_mV=4001, voltage_max_mV=4000)


def test_content_model_hrv_faulty_voltage2() -> None:
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="iv110", voltage_mV=4001, voltage_max_mV=4000)


def test_content_model_hrv_faulty_voltage3() -> None:
    with pytest.raises(ValidationError):
        _ = VirtualHarvesterConfig(name="iv110", voltage_mV=4000, voltage_min_mV=4001)


@pytest.mark.parametrize("name", ["ivcurves", "iv1000", "isc_voc"])
def test_content_model_hrv_faulty_emu(name: str) -> None:
    hrv = VirtualHarvesterConfig(name=name)
    with pytest.raises(ValidationError):
        _ = VirtualSourceConfig(name="dio_cap", harvester=hrv)


def test_content_model_src_min() -> None:
    VirtualSourceConfig(
        id=9999,
        name="new_src",
        owner="jane",
        group="wayne",
    )


def test_content_model_src_force_warning() -> None:
    src = VirtualSourceConfig(
        name="BQ25570",
        C_output_uF=200,
        C_intermediate_uF=100,
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)
    # -> triggers warning currently


def test_content_model_src_force_other_hysteresis1() -> None:
    src = VirtualSourceConfig(
        name="BQ25570",
        V_intermediate_enable_threshold_mV=4000,
        V_intermediate_disable_threshold_mV=3999,
        V_output_mV=2000,
        V_buck_drop_mV=100,
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)


def test_content_model_src_force_other_hysteresis2() -> None:
    src = VirtualSourceConfig(
        name="BQ25570",
        V_intermediate_enable_threshold_mV=1000,
        V_intermediate_disable_threshold_mV=999,
        V_output_mV=2000,
        V_buck_drop_mV=100,
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)
