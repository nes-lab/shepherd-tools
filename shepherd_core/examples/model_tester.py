from datetime import datetime
from datetime import timedelta

from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualHarvester
from shepherd_core.data_models.content import VirtualSource
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks

Experiment.dump_schema("experiment_schema.yaml")

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

xperi.to_file("experiment_dict.yaml")

xperi2 = Experiment.from_file("experiment_dict.yaml")

print(f"xp1 hash: {xperi.get_hash()}")
print(f"xp2 hash: {xperi2.get_hash()}")

tbt = TestbedTasks.from_xp(xperi2)
tbt.to_file("experiment_tb_tasks.yaml")
