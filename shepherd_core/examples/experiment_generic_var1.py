"""How-to for defining an experiment - variant 1.

What the code does:
- recommended approach for missing testbed-client
- variants
- var1 - references a server-path for the firmware
- var2 - embeds local firmware in yaml (elf-support is linux-only)
- assumption:
- start ASAP,
- no custom IDs,
- static Power-Supply
- no power-tracing

"""

from pathlib import Path

from shepherd_core import WebClient
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import MCU

# For online-queries the lib can be connected to the testbed-server.
# NOTE: there are 3 states:
# - unconnected -> demo-fixtures are queried (locally)
# - connected -> publicly available data is queried online
# - logged in with valid token -> also private data is queried online
do_connect = False
if do_connect:
    WebClient()

xp = Experiment(
    id="4567",
    name="meaningful_TestName",
    # time_start could be "2033-03-13 14:15:16" or "datetime.now() + timedelta(minutes=30)"
    duration=30,
    target_configs=[
        TargetConfig(
            target_IDs=range(7, 13),
            custom_IDs=range(1, 100),  # note: longer list is OK
            energy_env=EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
            firmware1=Firmware(
                name="FW_TestXYZ",
                data=Path("/var/shepherd/content/fw/nes_lab/nrf52_demo_rf/build.elf"),
                data_type=FirmwareDType.path_elf,
                data_local=False,
                mcu=MCU(name="nRF52"),
            ),
            power_tracing=None,
            gpio_tracing=GpioTracing(
                uart_decode=True,  # enables logging uart from userspace
                uart_baudrate=115_200,
            ),
        ),
    ],
)
xp.to_file("experiment_generic_var1.yaml")

# Create a tasks-list for the testbed
tb_tasks = TestbedTasks.from_xp(xp)
tb_tasks.to_file("experiment_generic_var1_tbt.yaml")

# next steps:
# - copy to server:
#   scp ./experiment_generic_varX_tbt.yaml user@shepherd.cfaed.tu-dresden.de:/var/shepherd/content/
# - run with herd-tool:
#   shepherd-herd --verbose run --attach /var/shepherd/content/experiment_generic_varX_tbt.yaml
