""" This example shows ways to embed firmware into the data-model
    Note: the new semi-automatic way to generate a data-model needs pwntools installed
          or shepherd-core[elf]
"""
from pathlib import Path

from shepherd_core import TestbedClient
from shepherd_core import fw_tools
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import FirmwareDType

path_elf = Path(__file__).parent.parent / "tests/fw_tools/build_msp.elf"

# Option 1 - fully manual

fw1 = Firmware(
    name="msp_deep_sleep",
    data=fw_tools.file_to_base64(path_elf),
    data_type=FirmwareDType.base64_elf,
    mcu={"name": "MSP430FR"},
    owner="example",
    group="test",
)

# Option 2 - semi-automatic

fw2 = Firmware.from_firmware(
    file=path_elf,
    name="msp_deep_sleep",
    owner="example",
    group="test",
)

# store embedded data with .extract_firmware(path)

# Option 3 - fully automatic (with login),

tb_client = TestbedClient()
# tb_client.connect(token="your_private_login_token")
# fw3 = Firmware.from_firmware(file=path_elf, name="msp_deep_sleep")
