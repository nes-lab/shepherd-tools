"""Converter for ELF-files."""

import subprocess  # ruff: ignore[suspicious-subprocess-import]
from pathlib import Path

from pydantic import validate_call

# extra src-file necessary to prevent circular import


@validate_call
def elf_to_hex(file_elf: Path, file_hex: Path | None = None) -> Path:
    """Convert ELF to hex file using objcopy."""
    if not file_elf.is_file():
        raise ValueError("Fn needs an existing file as input")
    if not file_hex:
        file_hex = file_elf.resolve().with_suffix(".hex")
    cmd = [
        "objcopy",
        "-I",
        "elf32-little",  # for MCUs with ARM Cortex-M, AVR, RISC-V, ESP32, MSP430, ...
        "-O",
        "ihex",
        file_elf.resolve().as_posix(),
        file_hex.as_posix(),
    ]
    # TODO: $ARCH-Versions of objcopy should be used
    #       .Hex of nRF / msp identical between the 3 $arch-versions of bincopy
    #       -> but this could break without warning
    # Fix1: use arm-none-eabi-objcopy in binutils-arm-none-eabi
    # Fix2: use x86_64-linux-gnu-objcopy in binutils-multiarch
    # -> try to locate all three with shutil.which()
    try:
        subprocess.run(cmd, check=True, shell=False)  # ruff: ignore[subprocess-without-shell-equals-true]
    except FileNotFoundError as err:
        raise RuntimeError(
            "Objcopy not found -> are binutils or build-essential installed?"
        ) from err
    except subprocess.CalledProcessError:
        raise RuntimeError("Objcopy failed to convert ELF to iHEX") from None
    return file_hex
