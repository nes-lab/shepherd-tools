"""Prepare TrafficBench to run as experiment on testbed."""

from pathlib import Path

from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.logger import log

from shepherd_core import WebClient
from shepherd_core import data_models as sm

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_task = Path("/var/shepherd/content/task/nes_lab/")
        path_fw = Path("/var/shepherd/content/fw/nes_lab/")
    else:
        path_task = path_here / "content/"
        path_fw = path_here / "content/fw/nes_lab/"

    do_connect = False
    if do_connect:
        # connected -> publicly available data is queried online
        WebClient()

    if not path_fw.exists():
        path_fw.mkdir(parents=True)
    if not path_task.exists():
        path_task.mkdir(parents=True)

    # RF-Survey
    exp = sm.Experiment(
        name="rf_survey",
        comment="generate link-matrix",
        duration=8 * 60,
        target_configs=[
            sm.TargetConfig(
                target_IDs=list(range(1, 12)),
                custom_IDs=list(range(1, 32)),
                # ⤷ note: traffic bench expects node 1 as root-node
                energy_env=sm.EnergyEnvironment(name="synthetic_static_3000mV_50mA"),
                firmware1=sm.Firmware.from_firmware(
                    file=path_fw / "nrf52_rf_survey/build.elf",
                    embed=False,
                    owner="Ingmar",
                    group="NES_Lab",
                ),
                firmware2=sm.Firmware(name="msp430_deep_sleep"),
                power_tracing=None,
                uart_logging=sm.UartLogging(baudrate=115_200),
            )
        ],
    )
    path_ret = TestbedTasks.from_xp(exp).to_file(path_task / "tasks_rf_survey")
    log.info("Wrote: %s", path_ret.as_posix())
