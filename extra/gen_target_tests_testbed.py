"""Create experiments for running target self-checks on testbed."""

from pathlib import Path

from shepherd_core import WebClient
from shepherd_core import data_models as sm

from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.logger import logger

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_task = Path("/var/shepherd/content/task/nes_lab/")
    else:
        path_task = path_here / "content/"

    do_connect = False
    if do_connect:
        # connected -> publicly available data is queried online
        WebClient()

    if not path_task.exists():
        path_task.mkdir(parents=True)

    # Self-test both ICs
    tests = [
        ("nrf52_testable", "msp430_testable", "target_device_test1_testbed"),
        ("nrf52_rf_test", "msp430_deep_sleep", "target_device_test2_testbed"),
        ("nrf52_deep_sleep", "msp430_deep_sleep", "target_device_test3_testbed"),
    ]

    for fw_nrf, fw_msp, name in tests:
        xp = sm.Experiment(
            name=name,
            comment="T1: shared-gpio, T2: rf-demo, T3: deep-sleep",
            duration=30,
            target_configs=[
                sm.TargetConfig(
                    target_IDs=list(range(1, 12)),
                    energy_env=sm.EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
                    firmware1=sm.Firmware(name=fw_nrf),
                    firmware2=sm.Firmware(name=fw_msp),
                    power_tracing=sm.PowerTracing(),
                    gpio_tracing=sm.GpioTracing(),
                    uart_tracing=sm.UartTracing(baudrate=115_200),
                )
            ],
        )
        path_ret = TestbedTasks.from_xp(xp).to_file(path_task / name)
        logger.info("Wrote: %s", path_ret.as_posix())
