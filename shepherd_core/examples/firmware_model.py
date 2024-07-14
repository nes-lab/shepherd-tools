"""This example shows ways to embed firmware into the data-model.

Note: the new semi-automatic way to generate a data-model needs pwntools installed
or shepherd-core[elf].
"""

from pathlib import Path

from shepherd_core import WebClient
from shepherd_core import fw_tools
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import FirmwareDType

path_elf = Path(__file__).parent.parent / "tests/fw_tools/build_msp.elf"

# Option 1 - fully manual

fw1 = Firmware(
    name="msp_deep_sleep1",
    data=fw_tools.file_to_base64(path_elf),
    data_type=FirmwareDType.base64_elf,
    mcu={"name": "MSP430FR"},
    owner="example",
    group="test",
)
fw1.to_file(Path(__file__).parent / "firmware.yaml")

# Option 2 - semi-automatic -> MCU and data-type get derived

fw2 = Firmware.from_firmware(
    file=path_elf,
    name="msp_deep_sleep2",
    owner="example",
    group="test",
)

# store embedded data
path_elf2 = fw2.extract_firmware(Path(__file__).parent)
print(f"stored firmware to '{path_elf2.name}'")


# Option 3 - fully automatic (with login) -> owner and group get prefilled

do_connect = False
if do_connect:
    WebClient(token="your_personal_login_token")  # noqa: S106
    fw3 = Firmware.from_firmware(file=path_elf, name="msp_deep_sleep3")
