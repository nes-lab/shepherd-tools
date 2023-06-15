import base64
import hashlib
import subprocess  # noqa: S404
from pathlib import Path
from typing import Optional

from pydantic import validate_arguments


@validate_arguments
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
    except FileNotFoundError:
        raise RuntimeError(
            "Objcopy not found -> are binutils or build-essential installed?"
        )
    if ret.returncode != 0:
        raise RuntimeError("Objcopy failed to convert ELF to iHEX")
    return file_hex


@validate_arguments
def file_to_base64(file_path: Path) -> str:
    if not file_path.is_file():
        raise ValueError("Fn needs an existing file as input")
    with open(file_path.resolve(), "rb") as file:
        file_content = file.read()
    return base64.b64encode(file_content).decode("ascii")


@validate_arguments
def base64_to_file(content: str, file_path: Path) -> None:
    file_content = base64.b64decode(content)
    with open(file_path.resolve(), "wb") as file:
        file.write(file_content)


@validate_arguments
def file_to_hash(file_path: Path) -> str:
    if not file_path.is_file():
        raise ValueError("Fn needs an existing file as input")
    with open(file_path.resolve(), "rb") as file:
        file_content = file.read()
    return hashlib.sha3_224(file_content).hexdigest()
