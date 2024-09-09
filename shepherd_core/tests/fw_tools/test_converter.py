from pathlib import Path

import pytest

from shepherd_core import fw_tools

from .conftest import files_elf


@pytest.fixture
def path_hex(tmp_path: Path) -> Path:
    path_elf = files_elf[0]
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    return fw_tools.elf_to_hex(path_elf, path_hex)


@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_elf_to_hex(path_elf: Path, tmp_path: Path) -> None:
    path_hex = (tmp_path / (path_elf.stem + ".hex")).resolve()
    path_gen = fw_tools.elf_to_hex(path_elf, path_hex)
    assert path_hex.exists()
    assert path_hex.as_posix() == path_gen.as_posix()


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_firmware_to_hex_w_elf(path_elf: Path) -> None:
    path_gen = fw_tools.firmware_to_hex(path_elf)
    assert path_gen.exists
    assert path_gen.suffix.lower() == ".hex"


@pytest.mark.elf
@pytest.mark.converter
def test_firmware_to_hex_w_hex(path_hex: Path) -> None:
    path_gen = fw_tools.firmware_to_hex(path_hex)
    assert path_gen.exists
    assert path_gen.suffix.lower() == ".hex"
    assert path_gen.as_posix() == path_hex.as_posix()


@pytest.mark.elf
@pytest.mark.converter
def test_firmware_to_hex_w_fail() -> None:
    path_some = Path(__file__).parent / "conftest.py"
    with pytest.raises(FileNotFoundError):
        _ = fw_tools.firmware_to_hex(path_some)


@pytest.mark.elf
@pytest.mark.converter
def test_hash() -> None:
    hash_a = fw_tools.file_to_hash(files_elf[0])
    hash_b = fw_tools.file_to_hash(files_elf[1])
    hash_c = fw_tools.file_to_hash(files_elf[1])
    assert hash_a != hash_b
    assert hash_b == hash_c


@pytest.mark.elf
@pytest.mark.converter
@pytest.mark.parametrize("path_elf", files_elf)
def test_base64(path_elf: Path, tmp_path: Path) -> None:
    b64_a = fw_tools.file_to_base64(path_elf)
    path_b = (tmp_path / path_elf.name).resolve()
    fw_tools.base64_to_file(b64_a, path_b)
    b64_b = fw_tools.file_to_base64(path_b)
    assert b64_a == b64_b
    hash_a = fw_tools.file_to_hash(path_elf)
    hash_b = fw_tools.file_to_hash(path_b)
    assert hash_a == hash_b


# extract_firmware() is indirectly tested with Firmware-Class
