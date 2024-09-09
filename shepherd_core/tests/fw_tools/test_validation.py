from pathlib import Path

import pytest

from shepherd_core import fw_tools
from shepherd_core.data_models import FirmwareDType

from .conftest import files_elf


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_elf_detection(path_elf: Path) -> None:
    assert fw_tools.is_elf(path_elf)
    if "nrf" in path_elf.name:
        assert fw_tools.is_elf_nrf52(path_elf)
    elif "msp" in path_elf.name:
        assert fw_tools.is_elf_msp430(path_elf)


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_elf_determination(path_elf: Path) -> None:
    assert fw_tools.determine_type(path_elf) == FirmwareDType.path_elf
    if "nrf" in path_elf.name:
        assert fw_tools.determine_arch(path_elf) == "nrf52"
    elif "msp" in path_elf.name:
        assert fw_tools.determine_arch(path_elf) == "msp430"


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_hex_detection(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    assert fw_tools.is_hex(path_hex)
    if "nrf" in path_elf.name:
        assert fw_tools.is_hex_nrf52(path_hex)
    elif "msp" in path_elf.name:
        assert fw_tools.is_hex_msp430(path_hex)


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_hex_determination(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_hex = fw_tools.elf_to_hex(path_elf, path_hex)
    assert fw_tools.determine_type(path_hex) == FirmwareDType.path_hex
    if "nrf" in path_elf.name:
        assert fw_tools.determine_arch(path_hex) == "nrf52"
    elif "msp" in path_elf.name:
        assert fw_tools.determine_arch(path_hex) == "msp430"
