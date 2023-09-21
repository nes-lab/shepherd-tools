"""


"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from shepherd_core import Reader as ShpReader
from shepherd_core import TestbedClient
from shepherd_core import Writer as ShpWriter
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.task import EmulationTask
from shepherd_core.data_models.task import ObserverTasks
from shepherd_core.data_models.task import ProgrammingTask
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import TargetPort
from shepherd_core.logger import logger


def generate_lab_vsrc(path: Path):
    # Config
    _V = 3.0
    _A = 50e-3
    duration_s = 60

    if path.exists():
        logger.info("File exists, will skip generating: %s", path.name)
        return

    with ShpWriter(path) as file:
        file.store_hostname("artificial")
        # values in SI units
        timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)
        voltage_vector = np.linspace(_V, _V, int(file.samplerate_sps * duration_s))
        current_vector = np.linspace(_A, _A, int(file.samplerate_sps * duration_s))
        file.append_iv_data_si(timestamp_vector, voltage_vector, current_vector)
    with ShpReader(path) as file:
        logger.info("Energy-Statistic of Env: %f", file.energy())
        file.save_metadata()


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if sys.platform.startswith("linux"):
        path_cfg = Path("/etc/shepherd/")
    else:
        path_cfg = path_here / "content/"
    path_rec = Path("/var/shepherd/recordings/")
    path_cnt = path_here / "content/"
    path_pwr = path_here / "content/lab_pwr_src.h5"

    tb_client = TestbedClient()
    do_connect = False
    if do_connect:
        tb_client.connect()

    # generate pwr-supply
    generate_lab_vsrc(path_pwr)

    # Self-test both ICs
    tests = [
        ("nrf52_testable", "msp430_testable", "target_device_test1"),
        ("nrf52_rf_test", "msp430_deep_sleep", "target_device_test2"),
        ("nrf52_deep_sleep", "msp430_deep_sleep", "target_device_test3"),
    ]

    for p_nrf, p_msp, name in tests:
        _path = ObserverTasks(
            observer="sheep0",
            owner_id=123,
            time_prep=datetime.now(),
            root_path=path_rec,
            abort_on_error=False,
            fw1_prog=ProgrammingTask(
                firmware_file=path_cnt / p_nrf / "build.hex",
                target_port=TargetPort.A,
                mcu_port=1,
                mcu_type="nRF52".lower(),
                protocol=ProgrammerProtocol.SWD,
            ),
            fw2_prog=ProgrammingTask(
                firmware_file=path_cnt / p_msp / "build.hex",
                target_port=TargetPort.A,
                mcu_port=2,
                mcu_type="MSP430FR".lower(),
                protocol=ProgrammerProtocol.SBW,
            ),
            emulation=EmulationTask(
                input_path=path_pwr,
                output_path=path_rec / (name + ".h5"),
                duration=30,
                enable_io=True,
                gpio_tracing=GpioTracing(
                    uart_decode=True,  # enables logging uart from userspace
                    uart_baudrate=115_200,
                ),
            ),
        ).to_file(path_cfg / name)
        logger.info("Wrote: %s", _path.as_posix())
