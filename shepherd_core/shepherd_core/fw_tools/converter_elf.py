import subprocess  # noqa: S404
from pathlib import Path
from typing import Optional

from pydantic import validate_call

# extra src-file necessary to prevent circular import


@validate_call
def elf_to_hex(file_elf: Path, file_hex: Optional[Path] = None) -> Path:
    if not file_elf.is_file():
        raise ValueError("Fn needs an existing file as input")
    if not file_hex:
        file_hex = file_elf.resolve().with_suffix(".hex")
    cmd = ["objcopy", "-O", "ihex", file_elf.resolve().as_posix(), file_hex.as_posix()]
    # TODO: observe - maybe $ARCH-Versions of objcopy are needed
    #  (hex of nRF / msp identical between the 3 $arch-versions)
    try:
        ret = subprocess.run(cmd)  # noqa: S603
    except FileNotFoundError as err:
        raise RuntimeError(
            "Objcopy not found -> are binutils or build-essential installed?"
        ) from err
    if ret.returncode != 0:
        raise RuntimeError("Objcopy failed to convert ELF to iHEX")
    return file_hex
