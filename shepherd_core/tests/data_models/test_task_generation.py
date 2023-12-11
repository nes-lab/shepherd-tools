from datetime import timedelta
from pathlib import Path

from shepherd_core import local_now
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import Experiment
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import TargetConfig
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.data_models.task import TestbedTasks as TasteBadTasks


def test_task_generation_file(tmp_path: Path) -> None:
    path = Path(__file__).with_name("example_config_experiment.yaml")
    xp1 = Experiment.from_file(path)
    tb_tasks = TasteBadTasks.from_xp(xp1)
    tb_tasks.to_file(tmp_path / "tbt1.yaml")


def test_task_generation_script(tmp_path: Path) -> None:
    hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")

    target_cfgs = [
        # first init similar to yaml
        TargetConfig(
            target_IDs=list(range(1, 4)),
            custom_IDs=list(range(3)),
            energy_env={"name": "SolarSunny"},
            virtual_source={"name": "diode+capacitor"},
            firmware1={"name": "nrf52_demo_rf"},
        ),
        # second Instance fully object-oriented
        TargetConfig(
            target_IDs=list(range(6, 9)),
            custom_IDs=list(range(7, 18)),
            energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
            virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="msp430_deep_sleep"),
        ),
    ]

    xperi = Experiment(
        id="4567",
        name="meaningful Test-Name",
        time_start=local_now() + timedelta(minutes=30),
        target_configs=target_cfgs,
    )

    tb_tasks = TasteBadTasks.from_xp(xperi)
    tb_tasks.to_file(tmp_path / "tbt2.yaml")
