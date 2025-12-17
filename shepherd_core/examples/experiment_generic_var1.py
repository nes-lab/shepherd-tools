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

import shepherd_core.data_models as sm
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import MCU

from shepherd_core import WebClient

# For online-queries the lib can be connected to the testbed-server.
# NOTE: there are 3 states:
# - unconnected -> demo-fixtures are queried (locally)
# - connected -> publicly available data is queried online
# - logged in with valid token -> also private data is queried online
do_connect = False
if do_connect:
    WebClient()

exp = sm.Experiment(
    name="meaningful_TestName",
    # time_start could be "2033-03-13 14:15:16" or "datetime.now() + timedelta(minutes=30)"
    duration=30,
    target_configs=[
        sm.TargetConfig(
            target_IDs=range(7, 12),
            custom_IDs=range(1, 100),  # note: longer list is OK
            energy_env=sm.EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
            firmware1=sm.Firmware(
                name="FW_TestXYZ",
                data=Path("/var/shepherd/content/fw/nes_lab/nrf52_demo_rf/build.elf"),
                data_type=sm.FirmwareDType.path_elf,
                data_2_copy=False,
                mcu=MCU(name="nRF52"),
            ),
            power_tracing=None,
            gpio_tracing=sm.GpioTracing(),
            uart_logging=sm.UartLogging(baudrate=115_200),
        ),
    ],
)
exp.to_file("experiment_generic_var1.yaml")

# Create a tasks-list for the testbed
tb_tasks = TestbedTasks.from_xp(exp)
tb_tasks.to_file("experiment_generic_var1_tbt.yaml")

# next steps:
# - copy to server:
#   scp ./experiment_generic_varX_tbt.yaml user@shepherd.cfaed.tu-dresden.de:/var/shepherd/content/
# - run with herd-tool:
#   shepherd-herd --verbose run --attach /var/shepherd/content/experiment_generic_varX_tbt.yaml
