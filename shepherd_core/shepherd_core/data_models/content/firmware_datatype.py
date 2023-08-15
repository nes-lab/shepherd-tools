from enum import Enum


class FirmwareDType(str, Enum):
    base64_hex = "hex"
    base64_elf = "elf"
    path_hex = "path_hex"
    path_elf = "path_elf"
