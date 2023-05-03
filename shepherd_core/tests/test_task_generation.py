from datetime import datetime
from datetime import timedelta
from pathlib import Path

from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import Experiment
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import TargetConfig
from shepherd_core.data_models import VirtualHarvester
from shepherd_core.data_models import VirtualSource
from shepherd_core.data_models.task import TestbedTasks


def test_task_generation_file():
    path = Path(__file__).with_name("example_config_experiment.yaml")
    xp1 = Experiment.from_file(path)
    tb_tasks = TestbedTasks.from_xp(xp1)
    tb_tasks.to_file(Path("tbt1.yaml"))


def test_task_generation_script():
    hrv = VirtualHarvester(name="mppt_bq_thermoelectric")

    target_cfgs = [
        # first init similar to yaml
        TargetConfig(
            target_IDs=list(range(3001, 3004)),
            custom_IDs=list(range(0, 3)),
            energy_env={"name": "SolarSunny"},
            virtual_source={"name": "diode+capacitor"},
            firmware1={"name": "nrf52_demo_rf"},
        ),
        # second Instance fully object-oriented
        TargetConfig(
            target_IDs=list(range(2001, 2005)),
            custom_IDs=list(range(7, 18)),
            energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
            virtual_source=VirtualSource(name="BQ25570-Schmitt", harvester=hrv),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="msp430_deep_sleep"),
        ),
    ]

    xperi = Experiment(
        id="4567",
        name="meaningful Test-Name",
        time_start=datetime.utcnow() + timedelta(minutes=30),
        target_configs=target_cfgs,
    )

    tb_tasks = TestbedTasks.from_xp(xperi)
    tb_tasks.to_file(Path("tbt2.yaml"))
