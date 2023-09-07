"""

How to define an experiment:

- within python (shown in this example)
    - object-oriented data-models of
        - experiment
        - TargetConfig -> shared for group of targets
        - virtualSource -> defines energy environment and converters
    - sub-elements reusable
    - scriptable for range of experiments
    - check for plausibility right away
- as yaml (shown in experiment_from_yaml.yaml)
    - default file-format for storing meta-data (for shepherd)
    - minimal writing
    - easy to copy parts
    - submittable through web-interface

"""
from datetime import datetime
from pathlib import Path

import numpy as np

from shepherd_core import BaseWriter as ShpWriter
from shepherd_core import TestbedClient
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware as FW
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import EmulationTask
from shepherd_core.data_models.task import ObserverTasks
from shepherd_core.data_models.task import ProgrammingTask as Pt
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import TargetPort
from shepherd_core.logger import logger


def generate_lab_vsrc(path: Path):
    # Config
    voltage_V = 3.0
    current_A = 50e-3
    duration_s = 60

    if path.exists():
        logger.info("File exists, will skip: %s", path.name)
    else:
        with ShpWriter(path) as file:
            file.store_hostname("artificial")
            # values in SI units
            timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)
            voltage_vector = np.linspace(
                voltage_V, voltage_V, int(file.samplerate_sps * duration_s)
            )
            current_vector = np.linspace(
                current_A, current_A, int(file.samplerate_sps * duration_s)
            )
            file.append_iv_data_si(timestamp_vector, voltage_vector, current_vector)


if __name__ == "__main__":
    path_cfg = Path("/etc/shepherd/")
    path_rec = Path("/var/shepherd/recordings/")
    path_here = Path(__file__).parent.absolute()
    path_cnt = path_here / "content/"
    path_pwr = path_here / "content/lab_pwr_src.h5"

    tb_client = TestbedClient()
    do_connect = False
    if do_connect:
        tb_client.connect()

    # generate pwr-supply
    generate_lab_vsrc(path_pwr)

    # Programmer Tasks: basics are TargetPort=A
    nrf = {
        "target_port": TargetPort.A,
        "mcu_port": 1,
        "mcu_type": "nRF52",
        "protocol": ProgrammerProtocol.SWD,
    }
    _nrf_test = Pt(firmware_file=path_cnt / "nrf52_testable/build.elf", **nrf)
    _nrf_send = Pt(firmware_file=path_cnt / "nrf52_rf_test/build.elf", **nrf)
    _nrf_sleep = Pt(firmware_file=path_cnt / "nrf52_deep_sleep/build.elf", **nrf)
    _nrf_survey = Pt(firmware_file=path_cnt / "nrf52_rf_survey/build.elf", **nrf)

    msp = {
        "target_port": TargetPort.A,
        "mcu_port": 2,
        "mcu_type": "MSP430FR",
        "protocol": ProgrammerProtocol.SBW,
    }
    _msp_test = Pt(firmware_file=path_cnt / "msp430_testable/build.elf", **msp)
    _msp_sleep = Pt(firmware_file=path_cnt / "msp430_deep_sleep/build.elf", **msp)

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
                gpio_tracing=GpioTracing(),
            )
        ],
    )
    TestbedTasks.from_xp(xp1).to_file(path_here / "content/tb_tasks_rf_survey")

    # Self-test both ICs
    obs_def = {
        "observer": "sheep0",
        "owner_id": 123,
        "time_prep": datetime.now(),
        "root_path": path_rec,
        "abort_on_error": False,
    }
    # Target Device-Test 1
    ObserverTasks(
        **obs_def,
        fw1_prog=_nrf_test,
        fw2_prog=_msp_test,
        emulation=EmulationTask(
            input_path=path_pwr,
            output_path=path_rec / "tgt_test1_.h5",
            power_tracing=None,
        ),
    ).to_file(path_cfg / "test_target1")
    # Target Device-Test 2
    ObserverTasks(
        **obs_def,
        fw1_prog=_nrf_send,
        fw2_prog=_msp_sleep,
        emulation=EmulationTask(
            input_path=path_pwr,
            output_path=path_rec / "tgt_test2_.h5",
            power_tracing=None,
        ),
    ).to_file(path_cfg / "test_target2")
    # Target Device-Test 3
    ObserverTasks(
        **obs_def,
        fw1_prog=_nrf_sleep,
        fw2_prog=_msp_sleep,
        emulation=EmulationTask(
            input_path=path_pwr,
            output_path=path_rec / "tgt_test3_.h5",
            power_tracing=None,
        ),
    ).to_file(path_cfg / "test_target3")
