import shutil
from pathlib import Path

from shepherd_core import fw_tools
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import FirmwareDType

path_src = Path(__file__).parent.parent / "tests/fw_tools/build_msp.elf"
path_elf = Path(__file__).with_name("firmware.elf")

#
shutil.copy(path_src, path_elf)

print(f"UID old = {fw_tools.read_uid(path_elf)}")
fw_tools.modify_uid(path_elf, 0xCAFE)
print(f"UID new = {fw_tools.read_uid(path_elf)}")

path_hex = fw_tools.elf_to_hex(path_elf)

b64 = fw_tools.file_to_base64(path_elf)

fw = Firmware(
    name="msp_deep_sleep",
    data=b64,
    data_type=FirmwareDType.base64_hex,
    mcu={"name": "MSP430FR"},
    owner="example",
    group="test",
)
# TODO: make that process easier
#  -> logged in with .from_file() almost everything can be deducted
