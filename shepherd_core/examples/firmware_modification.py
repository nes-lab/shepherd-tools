"""This example manipulates elf-files and embeds firmware into the data-model.

Note: make sure to have installed
- shepherd-core[elf] via pip
- build-essential or binutils-$ARCH installed.
"""

import shutil
from pathlib import Path

from shepherd_core import fw_tools
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import FirmwareDType

path_src = Path(__file__).parent.parent / "tests/fw_tools/build_msp.elf"
path_elf = Path(__file__).with_name("firmware_msp.elf")

# make local copy to play with
shutil.copy(path_src, path_elf)

print(f"UID old = 0x{fw_tools.read_uid(path_elf):X}")
fw_tools.modify_uid(path_elf, 0xCAFE)
print(f"UID new = 0x{fw_tools.read_uid(path_elf):X}")

path_hex = fw_tools.elf_to_hex(path_elf)

# just PoC - there is an easier way to generate data-model, see other fw-example
b64 = fw_tools.file_to_base64(path_elf)

fw = Firmware(
    name="msp_deep_sleep",
    data=b64,
    data_type=FirmwareDType.base64_elf,
    mcu={"name": "MSP430FR"},
    owner="example",
    group="test",
)

# for completion also generate hex for nrf
path_src = Path(__file__).parent.parent / "tests/fw_tools/build_nrf.elf"
path_elf = Path(__file__).with_name("firmware_nrf.elf")
shutil.copy(path_src, path_elf)
fw_tools.elf_to_hex(path_elf)
