from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import validate_call
from typing_extensions import Annotated

from ..commons import uid_len_default
from ..commons import uid_str_default
from ..logger import logger as log
from .validation import is_elf

try:
    from pwnlib.elf import ELF

    elf_support = True
except ImportError as e:
    elf_support = False
    elf_error_text = (
        "Please install functionality with 'pip install shepherd_core[elf] -U' first, "
        f"underlying exception: {e.msg}"
    )


@validate_call
def find_symbol(file_elf: Path, symbol: str) -> bool:
    if symbol is None or not is_elf(file_elf):
        return False
    if not elf_support:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    try:
        elf.symbols[symbol]
    except KeyError:
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
def read_symbol(
    file_elf: Path, symbol: str, length: int = uid_len_default
) -> Optional[int]:
    """interpreted as int"""
    if not find_symbol(file_elf, symbol):
        return None
    if not elf_support:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    addr = elf.symbols[symbol]
    value_raw = elf.read(address=addr, count=length)[-length:]
    elf.close()
    return int.from_bytes(bytes=value_raw, byteorder=elf.endian, signed=False)


def read_uid(file_elf: Path) -> Optional[int]:
    return read_symbol(file_elf, symbol=uid_str_default, length=uid_len_default)


def read_arch(file_elf: Path) -> Optional[str]:
    if not is_elf(file_elf):
        return None
    if not elf_support:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    if "exec" in elf.elftype.lower():
        return elf.arch.lower()
    log.error("ELF is not Executable")
    return None


@validate_call
def modify_symbol_value(
    file_elf: Path,
    symbol: str,
    value: Annotated[int, Field(ge=0, lt=2 ** (8 * uid_len_default))],
    overwrite: bool = False,
) -> Optional[Path]:
    """replaces value of symbol in ELF-File, hardcoded for uint16_t (2 byte)
    testbed uses FN to patch firmware with custom target-ID
    NOTE: can overwrite provided file

    """
    if not find_symbol(file_elf, symbol):
        return None
    if not elf_support:
        raise RuntimeError(elf_error_text)
    elf = ELF(path=file_elf)
    addr = elf.symbols[symbol]
    value_raw = elf.read(address=addr, count=uid_len_default)[-uid_len_default:]
    # ⤷ cutting needed -> msp produces 4b instead of 2
    value_old = int.from_bytes(bytes=value_raw, byteorder=elf.endian, signed=False)
    value_raw = value.to_bytes(
        length=uid_len_default, byteorder=elf.endian, signed=False
    )
    elf.write(address=addr, data=value_raw)
    if overwrite:
        file_new = file_elf
    else:
        file_new = file_elf.with_name(
            file_elf.stem + "_" + str(value) + file_elf.suffix
        )
        # could be simplified, but py3.8-- doesn't know .with_stem()
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


def modify_uid(file_elf: Path, value: int) -> Optional[Path]:
    return modify_symbol_value(
        file_elf, symbol=uid_str_default, value=value, overwrite=True
    )
