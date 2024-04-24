"""Separated data-type.

Done due to cyclic inheritance.
"""

from enum import Enum


class FirmwareDType(str, Enum):
    """Options for firmware-types."""

    base64_hex = "hex"
    base64_elf = "elf"
    path_hex = "path_hex"
    path_elf = "path_elf"
