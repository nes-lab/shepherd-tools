"""Helper-functions for handling firmware around the testbed."""

from typing import Any

try:
    from importlib.util import find_spec

    find_spec("pwnlib.elf.ELF")
except ImportError:
    # replace missing dependencies from elf-only pwntools
    import sys
    from importlib.util import find_spec
    from unittest.mock import MagicMock

    class Mock(MagicMock):
        @classmethod
        def __getattr__(cls, name: str) -> Any:
            return MagicMock()

    MOCK_MODULES = [
        "socks",  # general lib-init / context-init
        "serial",
        # troublemaker on bbone and/or windows
        "capstone",
        "paramiko",
        "unicorn",
        "cffi",
    ]
    # only update when module is not avail
    MOCK_MODULES = [mod_name for mod_name in MOCK_MODULES if find_spec(mod_name) is None]
    sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

from .converter import base64_to_file
from .converter import base64_to_hash
from .converter import extract_firmware
from .converter import file_to_base64
from .converter import file_to_hash
from .converter import firmware_to_hex
from .converter_elf import elf_to_hex
from .patcher import find_symbol
from .patcher import modify_symbol_value
from .patcher import modify_uid
from .patcher import read_arch
from .patcher import read_symbol
from .patcher import read_uid
from .validation import determine_arch
from .validation import determine_type
from .validation import is_elf
from .validation import is_elf_msp430
from .validation import is_elf_nrf52
from .validation import is_hex
from .validation import is_hex_msp430
from .validation import is_hex_nrf52

__all__ = [
    # patcher
    "read_uid",
    "modify_uid",
    "modify_symbol_value",
    "find_symbol",
    "read_symbol",
    "read_arch",
    # converter
    "elf_to_hex",
    "file_to_base64",
    "base64_to_file",
    "file_to_hash",
    "base64_to_hash",
    "extract_firmware",
    "firmware_to_hex",
    # validation
    "is_hex",
    "is_hex_msp430",
    "is_hex_nrf52",
    "is_elf",
    "is_elf_msp430",
    "is_elf_nrf52",
    "determine_type",
    "determine_arch",
]
