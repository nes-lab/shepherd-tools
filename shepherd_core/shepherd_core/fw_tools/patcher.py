"""Read and modify symbols in ELF-files."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from pydantic import Field
from pydantic import validate_call

from shepherd_core.config import config
from shepherd_core.logger import log

from .validation import is_elf

try:
    from pwnlib.elf import ELF
except ImportError as e:
    ELF = None
    elf_error_text = (
        "Please install functionality with 'pip install shepherd-core[elf] -U' first, "
        f"underlying exception: {e.msg}"
    )


@validate_call
def find_symbol(file_elf: Path, symbol: str) -> bool:
    """Find a symbol in the ELF file."""
    if symbol is None or not is_elf(file_elf):
        return False
    if ELF is None:
        raise RuntimeError(elf_error_text)
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # switcheroo that also prevents windows bug (overwrite fails)
        file_tmp = Path(tmp) / file_elf.name
        shutil.copy(file_elf, file_tmp)
        elf = ELF(path=file_tmp)
        try:
            addr = elf.symbols[symbol]
        except KeyError:
            addr = None
        if addr is None:
            elf.close()  # better be safe
            log.debug("Symbol '%s' not found in ELF-File %s", symbol, file_elf.name)
            return False
        log.debug(
            "Symbol '%s' found in ELF-File %s, arch=%s, order=%s",
            symbol,
            file_elf.name,
            elf.arch,
            elf.endian,
        )
        elf.close()
    return True


@validate_call
def read_symbol(file_elf: Path, symbol: str, length: int) -> int | None:
    """Read value of symbol in ELF-File.

    Will be interpreted as int.
    """
    if not find_symbol(file_elf, symbol):
        return None
    if ELF is None:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    addr = elf.symbols[symbol]
    value_raw = elf.read(address=addr, count=length)[-length:]
    endian = elf.endian
    elf.close()
    return int.from_bytes(bytes=value_raw, byteorder=endian, signed=False)


def read_uid(file_elf: Path) -> int | None:
    """Read value of UID-symbol for shepherd testbed."""
    return read_symbol(file_elf, symbol=config.UID_NAME, length=config.UID_SIZE)


def read_arch(file_elf: Path) -> str | None:
    """Determine chip-architecture from elf-metadata."""
    if not is_elf(file_elf):
        return None
    if ELF is None:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    elf_type = elf.elftype.lower()
    elf_arch = elf.arch.lower()
    elf.close()
    if "exec" in elf_type:
        return elf_arch
    log.error("ELF is not Executable")
    return None


@validate_call
def modify_symbol_value(
    file_elf: Path,
    symbol: str,
    value: Annotated[int, Field(ge=0, lt=2 ** (8 * config.UID_SIZE))],
    *,
    overwrite: bool = False,
) -> Path | None:
    """Replace value of uint16-symbol in ELF-File.

    Hardcoded for uint16_t (2 byte).
    The testbed uses this to patch firmware with custom target-ID.

    NOTE: can overwrite provided file.

    """
    if not find_symbol(file_elf, symbol):
        return None
    if ELF is None:
        raise RuntimeError(elf_error_text)
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # switcheroo that also prevents windows bug (overwrite fails)
        file_tmp = Path(tmp) / file_elf.name
        shutil.copy(file_elf, file_tmp)

        elf = ELF(path=file_elf)
        addr = elf.symbols[symbol]
        value_raw = elf.read(address=addr, count=config.UID_SIZE)[-config.UID_SIZE :]
        # ⤷ cutting needed -> msp produces 4b instead of 2
        value_old = int.from_bytes(bytes=value_raw, byteorder=elf.endian, signed=False)
        value_raw = value.to_bytes(length=config.UID_SIZE, byteorder=elf.endian, signed=False)

        try:
            elf.write(address=addr, data=value_raw)
        except AttributeError:
            log.warning("ELF-Modifier failed @%s for symbol '%s'", f"0x{addr:X}", symbol)
            elf.close()
            return None

        file_new = file_elf if overwrite else file_elf.with_stem(file_elf.stem + "_" + str(value))
        try:
            file_new.unlink(missing_ok=True)
        except PermissionError:
            elf.close()
            log.error(
                "Failed to overwrite file, because it's somehow still in use (typical for WinOS)."
            )
            return None
        elf.save(path=file_new)
        elf.close()

    log.debug(
        "Value of Symbol '%s' modified: %s -> %s @%s",
        symbol,
        hex(value_old),
        hex(value),
        hex(addr),
    )
    return file_new


def modify_uid(file_elf: Path, value: int) -> Path | None:
    """Replace value of UID-symbol for shepherd testbed."""
    return modify_symbol_value(file_elf, symbol=config.UID_NAME, value=value, overwrite=True)
