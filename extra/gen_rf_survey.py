"""


"""
import sys
from pathlib import Path

from shepherd_core import TestbedClient
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware as FW
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if sys.platform.startswith("linux"):
        path_cfg = Path("/etc/shepherd/")
    else:
        path_cfg = path_here / "content/"
    path_cnt = path_here / "content/"

    tb_client = TestbedClient()
    do_connect = False
    if do_connect:
        tb_client.connect()

    # RF-Survey
    xp1 = Experiment(
        name="rf_survey",
        comment="generate link-matrix",
        duration=4 * 60,
        target_configs=[
            TargetConfig(
                target_IDs=list(range(3000, 3010)),
                custom_IDs=list(range(0, 99)),  # note: longer list is OK
                energy_env=EnergyEnvironment(name="eenv_static_3300mV_50mA_3600s"),
                virtual_source=VirtualSourceConfig(name="direct"),
                firmware1=FW.from_firmware(path_cnt / "nrf52_rf_survey/build.elf"),
                firmware2=FW.from_firmware(path_cnt / "msp430_deep_sleep/build.elf"),
                power_tracing=None,
                gpio_tracing=GpioTracing(
                    uart_decode=True,  # enables logging uart from userspace
                    uart_baudrate=115_200,
                ),
            )
        ],
    )
    TestbedTasks.from_xp(xp1).to_file(path_cfg / "tasks_rf_survey")
