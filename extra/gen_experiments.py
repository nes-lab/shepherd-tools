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
from pathlib import Path

from shepherd_core import TestbedClient
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()

    tb_client = TestbedClient()
    do_connect = False
    if do_connect:
        tb_client.connect()

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
                firmware1=Firmware(name="nrf52_rf_survey"),
                firmware2=Firmware(name="msp430_deep_sleep"),
                power_tracing=None,
                gpio_tracing=GpioTracing(),
            )
        ],
    )
    TestbedTasks.from_xp(xp1).to_file(path_here / "content" / "tb_tasks_rf_survey")

    # TODO: self-test both ICs
