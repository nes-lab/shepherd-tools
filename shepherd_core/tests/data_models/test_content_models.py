from pathlib import Path

import pytest
from pydantic import ValidationError
from shepherd_core.data_models import EnergyProfile
from shepherd_core.data_models.content import EnergyDType
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import FirmwareDType
from shepherd_core.data_models.content import VirtualHarvesterConfig
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.content.virtual_source_config import ConverterPRUConfig
from shepherd_core.data_models.content.virtual_storage_config import VirtualStorageConfig
from shepherd_core.data_models.testbed import MCU

from shepherd_core import fw_tools

from .conftest import files_elf


@pytest.fixture
def energy_profiles(tmp_path: Path) -> list[EnergyProfile]:
    path1 = Path(tmp_path) / "shp1.h5"
    path2 = Path(tmp_path) / "shp3.h5"
    path1.touch()
    path2.touch()
    profile1 = EnergyProfile(
        data_path=path1,
        data_type=EnergyDType.ivtrace,
        valid=True,
        energy_Ws=1.0,
        duration=23,
    )
    profile2 = EnergyProfile(
        data_path=path2,
        data_type=EnergyDType.ivtrace,
        valid=True,
        energy_Ws=3.0,
        duration=20,
    )
    return [profile1, profile2]


# ############################ Energy Profiles


def test_content_model_energy_profile_min1() -> None:
    EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
    )


def test_content_model_energy_profile_min2() -> None:
    EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.ivcurve,
        duration=999,
        energy_Ws=3.1,
    )


def test_content_model_energy_profile_autocast() -> None:
    EnergyProfile(
        data_path="./file",  # Path is expected
        data_type="ivcurve",  # enum is expected
        duration=999,
        energy_Ws=3.1,
    )


def test_content_model_energy_profile_derive_from_file(data_h5: Path) -> None:
    ep = EnergyProfile.derive_from_file(data_h5)
    assert ep.check() is True
    assert ep.valid is True


def test_content_model_energy_profile_check_fail(energy_profiles: list[EnergyProfile]) -> None:
    for profile in energy_profiles:
        assert profile.check() is False


def test_content_model_energy_profile_export_file(
    energy_profiles: list[EnergyProfile], tmp_path: Path
) -> None:
    assert len(energy_profiles) >= 1
    ep_file = tmp_path / "ep1.h5"
    assert not ep_file.exists()
    energy_profiles[0].export(ep_file)
    assert ep_file.exists()


def test_content_model_energy_profile_export_path(
    energy_profiles: list[EnergyProfile], tmp_path: Path
) -> None:
    assert len(energy_profiles) >= 1
    ep_file = tmp_path / "subpath" / energy_profiles[0].data_path.name
    assert not ep_file.parent.exists()
    ep_file.parent.mkdir(parents=True, exist_ok=False)
    assert not ep_file.exists()
    energy_profiles[0].export(ep_file.parent)
    assert ep_file.exists()


def test_content_model_energy_profile_export_error1(energy_profiles: list[EnergyProfile]) -> None:
    assert len(energy_profiles) >= 1
    ep_file = energy_profiles[0].data_path.parent / "random.h5"
    assert not ep_file.exists()
    ep_file.touch()
    with pytest.raises(FileExistsError):
        energy_profiles[0].export(ep_file)


def test_content_model_energy_profile_export_error2(tmp_path: Path) -> None:
    ep = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
    )
    with pytest.raises(FileNotFoundError):
        ep.export(tmp_path)


# ############################ Energy Environments


def test_content_model_energy_environment_min(energy_profiles: list[EnergyProfile]) -> None:
    EnergyEnvironment(
        id=9999,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )


def test_content_model_energy_environment_fail_empty() -> None:
    with pytest.raises(ValidationError):
        EnergyEnvironment(
            id=9999,
            name="some",
            energy_profiles=[],
            owner="jane",
            group="wayne",
        )


def test_content_model_energy_environment_properties(energy_profiles: list[EnergyProfile]) -> None:
    ee = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    assert ee.duration > 0
    assert len(ee) == len(energy_profiles)
    assert not ee.repetitions_ok
    assert ee.valid
    ee.enforce_validity()


def test_content_model_energy_environment_add_profile(energy_profiles: list[EnergyProfile]) -> None:
    ee1 = EnergyEnvironment(
        id=9765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    ee2 = ee1 + energy_profiles[0]
    assert len(ee2) == len(ee1) + 1


def test_content_model_energy_environment_add_profiles(
    energy_profiles: list[EnergyProfile],
) -> None:
    assert len(energy_profiles) >= 2
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    ee2 = ee1 + energy_profiles
    assert len(ee2) == len(ee1) + len(energy_profiles)


def test_content_model_energy_environment_add_env(energy_profiles: list[EnergyProfile]) -> None:
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    ee2 = ee1 + ee1
    assert len(ee2) == 2 * len(ee1)


def test_content_model_energy_environment_influence_duration(
    energy_profiles: list[EnergyProfile],
) -> None:
    assert len(energy_profiles) >= 1
    dur_now = 1000
    assert any(ep.duration < dur_now for ep in energy_profiles)
    ep = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=dur_now,
        energy_Ws=0.1,
    )
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=[ep],
        owner="jane",
        group="wayne",
    )
    assert ee1.duration == dur_now
    ee2 = ee1 + energy_profiles
    assert ee2.duration < dur_now


def test_content_model_energy_environment_influence_rep_ok(
    energy_profiles: list[EnergyProfile],
) -> None:
    assert len(energy_profiles) >= 1
    assert not all(ep.repetitions_ok for ep in energy_profiles)
    ep1 = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
        repetitions_ok=True,
    )
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=[ep1],
        owner="jane",
        group="wayne",
    )
    # only repeat if all embedded profiles support repetition
    assert len(ee1.energy_profiles) == 1
    assert len(ee1) >= 100
    ee2 = ee1 + energy_profiles
    assert len(ee2) >= 1 + len(energy_profiles)
    # the property should reflect that
    assert ee1.repetitions_ok
    assert not ee2.repetitions_ok


def test_content_model_energy_environment_influence_validity(
    energy_profiles: list[EnergyProfile],
) -> None:
    assert len(energy_profiles) >= 1
    assert all(ep.valid for ep in energy_profiles)
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    assert ee1.valid
    ee1.enforce_validity()  # forcing validity is fine
    # add one foul egg
    ep2 = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
        valid=False,
    )
    ee2 = ee1 + ep2
    assert not ee2.valid
    with pytest.raises(ValueError):  # noqa: PT011
        ee2.enforce_validity()


def test_content_model_energy_environment_get_item(energy_profiles: list[EnergyProfile]) -> None:
    assert len(energy_profiles) >= 1
    assert not all(ep.repetitions_ok for ep in energy_profiles)
    ep1 = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
        repetitions_ok=True,
    )
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=5 * [ep1],
        owner="jane",
        group="wayne",
    )
    assert ee1.repetitions_ok
    assert len(ee1.energy_profiles) == 5
    assert len(ee1) > 5
    # access with rep_ok is unbound
    for selection in [-200, -6, -5, -1, -0, 0, 1, 5, 6, 200]:
        _ = ee1[selection]
    # invalid selections
    for selection in ["boo", 0.0, None]:
        with pytest.raises(IndexError):
            _ = ee1[selection]
    # loose rep_ok status and repeat
    ee2 = ee1 + energy_profiles
    assert not ee2.repetitions_ok
    assert len(ee2) == len(ee2.energy_profiles)
    lenee = len(ee2.energy_profiles)
    for selection in [-lenee, -1, -0, 0, 1, lenee - 1]:
        _ = ee2[selection]
    # provoke some IndexError on usual lists
    for selection in [-200, -lenee - 1, lenee, 200]:
        with pytest.raises(IndexError):
            _ = ee2[selection]


def test_content_model_energy_environment_get_slice_rep_ok(
    energy_profiles: list[EnergyProfile],
) -> None:
    ep1 = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
        repetitions_ok=True,
    )
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=5 * [ep1],
        owner="jane",
        group="wayne",
    )
    assert ee1.repetitions_ok
    assert len(ee1.energy_profiles) == 5
    assert len(ee1) > 5
    # access while rep_ok
    assert len(ee1[:15].energy_profiles) == 15 - 0
    assert len(ee1[3:].energy_profiles) == ee1.PROFILES_MAX - 3
    assert len(ee1[3:2].energy_profiles) == 0
    assert len(ee1[6:7].energy_profiles) == 1  # would be 0 when unrepeated
    # TODO: negative access unsolved


def test_content_model_energy_environment_get_slice_no_rep(
    energy_profiles: list[EnergyProfile],
) -> None:
    ep1 = EnergyProfile(
        data_path=Path("./file"),
        data_type=EnergyDType.isc_voc,
        duration=1,
        energy_Ws=0.1,
        repetitions_ok=False,
    )
    ep_len = 5
    ee1 = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=ep_len * [ep1],
        owner="jane",
        group="wayne",
    )
    assert not ee1.repetitions_ok
    assert len(ee1.energy_profiles) == ep_len
    assert len(ee1) == ep_len
    # access identical to list
    for sli in [
        slice(15),
        slice(3, None),
        slice(3, 2),
        slice(6, 7),
        slice(-1),
        slice(-1, 3),
        slice(-3, -1),
    ]:
        assert len(ee1[sli].energy_profiles) == len(list(range(ep_len))[sli])


def test_content_model_energy_environment_export(
    tmp_path: Path, energy_profiles: list[EnergyProfile]
) -> None:
    assert len(energy_profiles) >= 1
    ee_path = tmp_path / "ee1234"
    ee = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=energy_profiles,
        owner="jane",
        group="wayne",
    )
    assert not ee_path.exists()
    ee.export(ee_path)
    assert ee_path.exists()
    assert len(list(ee_path.iterdir())) == len(energy_profiles) + 1
    # Fail because dir does already exist
    ee_path = tmp_path / "ee5678"
    ee_path.mkdir()
    assert ee_path.exists()
    with pytest.raises(FileExistsError):
        ee.export(ee_path)


def test_content_model_energy_environment_check(data_h5: Path) -> None:
    ep = EnergyProfile.derive_from_file(data_h5)
    assert ep.check() is True
    assert ep.valid is True
    ee = EnergyEnvironment(
        id=98765,
        name="some",
        energy_profiles=5 * [ep],
        owner="jane",
        group="wayne",
    )
    assert ee.check()
    assert ee.valid


# ############################ Firmware


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


# ############################ Virtual Harvester


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
        name="ivsurface", voltage_min_mV=1000, voltage_max_mV=4000, samples_n=11
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


@pytest.mark.parametrize("name", ["ivsurface", "iv1000", "isc_voc"])
def test_content_model_hrv_faulty_emu(name: str) -> None:
    hrv = VirtualHarvesterConfig(name=name)
    with pytest.raises(ValidationError):
        _ = VirtualSourceConfig(name="dio_cap", harvester=hrv)


# ############################ Virtual Source


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
        storage=VirtualStorageConfig.capacitor(C_uF=100, V_rated=6.3),
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)
    # -> triggers warning currently


def test_content_model_src_force_other_hysteresis1() -> None:
    src = VirtualSourceConfig(
        name="BQ25570",
        V_intermediate_enable_output_threshold_mV=4000,
        V_intermediate_disable_output_threshold_mV=3999,
        V_output_mV=2000,
        V_buck_drop_mV=100,
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)


def test_content_model_src_force_other_hysteresis2() -> None:
    src = VirtualSourceConfig(
        name="BQ25570",
        V_intermediate_enable_output_threshold_mV=1000,
        V_intermediate_disable_output_threshold_mV=999,
        V_output_mV=2000,
        V_buck_drop_mV=100,
    )
    ConverterPRUConfig.from_vsrc(src, dtype_in=EnergyDType.ivsample)
