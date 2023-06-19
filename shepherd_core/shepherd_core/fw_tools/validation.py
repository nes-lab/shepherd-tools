""" TODO: Work in Progress

"""
import os
import tempfile
from pathlib import Path

from elftools.common.exceptions import ELFError
from intelhex import IntelHex
from intelhex import IntelHexError
from pwnlib.elf import ELF
from pydantic import validate_arguments

from ..logger import logger
from . import elf_to_hex


@validate_arguments
def is_hex(file: Path):
    try:
        _ = IntelHex(file.as_posix())
    except ValueError:  # parsing
        return False
    except IntelHexError:  # structural errors
        return False
    return True


def is_hex_msp430(file: Path):
    """Observations:
    - addresses begin at 0x4000
    - value @0xFFFE (IVT) is start_address (of pgm-code)
    """
    if is_hex(file):
        ih = IntelHex(file.as_posix())
        if ih.minaddr() != 0x4000:
            return False
        if 0xFFFE not in ih.addresses():
            return False
        value = int.from_bytes(ih.gets(0xFFFE, 2), byteorder="little", signed=False)
        if 0x4000 > value >= 0xFF80:
            return False
        if ih.get_memory_size() >= 270_000:
            # conservative test for now - should be well below 128 kB + 8kB for msp430fr5962
            return False
        return True
    return False


def is_hex_nrf52(file: Path) -> bool:
    """Observations:
    - addresses begin at 0x0
    - only one segment (.get_segments), todo
    """
    if is_hex(file):
        ih = IntelHex(file.as_posix())
        if ih.minaddr() != 0x0000:
            return False
        if ih.get_memory_size() >= 1310720:
            # conservative test for now - should be well below 1 MB + 256 kB
            return False
        return True
    return False


@validate_arguments
def is_elf(file: Path) -> bool:
    if not os.path.isfile(file):
        return False
    try:
        _ = ELF(path=file)
    except ELFError:
        logger.debug("File %s is not ELF - Magic number does not match", file.name)
        return False
    return True


def is_elf_msp430(file: Path) -> bool:
    if is_elf(file):
        with tempfile.TemporaryDirectory() as path:
            file_hex = Path(path) / "file.hex"
            file_hex = elf_to_hex(file, file_hex)
            if is_hex_msp430(file_hex):
                return True
        return False
    return False


def is_elf_nrf52(file: Path) -> bool:
    if is_elf(file):
        with tempfile.TemporaryDirectory() as path:
            file_hex = Path(path) / "file.hex"
            file_hex = elf_to_hex(file, file_hex)
            if is_hex_nrf52(file_hex):
                return True
        return False
    return False
