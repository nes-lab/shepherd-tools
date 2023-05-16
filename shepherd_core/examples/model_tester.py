from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualHarvester
from shepherd_core.data_models.content import VirtualSource
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks

Experiment.dump_schema("experiment_schema.yaml")

"""

How to define an experiment:

- within python (shown in this example)
    - object-oriented
    - sub-elements reusable
    - scriptable for suite of experiments
    - check for plausibility right away 
- as yaml (shown in experiment_from_yaml.yaml)
    - minimal writing
    - easily copyable
    - submittable through web-interface

"""

hrv = VirtualHarvester(name="mppt_bq_thermoelectric")

target_cfgs = [
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
        custom_IDs=list(range(7, 18)),  # note: longer list is OK
        energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
        virtual_source=VirtualSource(name="BQ25570-Schmitt", harvester=hrv),
        firmware1=Firmware(name="nrf52_demo_rf"),
        firmware2=Firmware(name="msp430_deep_sleep"),
    ),
]

xperi1 = Experiment(
    id="4567",
    name="meaningful Test-Name",
    # time_start=datetime.utcnow() + timedelta(minutes=30),
    time_start="2033-03-13 14:15:16",
    target_configs=target_cfgs,
)

# Safe, reload and compare content
xperi1.to_file("experiment_from_py.yaml")
xperi2 = Experiment.from_file("experiment_from_py.yaml")
print(f"xp1 hash: {xperi1.get_hash()}")
print(f"xp2 hash: {xperi2.get_hash()}")

# comparison to same config (in yaml) fails due to internal variables, BUT:
xperi3 = Experiment.from_file("experiment_from_yaml.yaml")
print(f"xp3 hash: {xperi3.get_hash()} (won't match)")

# Create a tasks-list for the testbed
tb_tasks2 = TestbedTasks.from_xp(xperi2)
tb_tasks2.to_file("experiment_tb_tasks.yaml")

# Comparison between task-Lists succeed (experiment-comparison failed)
tb_tasks3 = TestbedTasks.from_xp(xperi3)
print(f"tasks2 hash: {tb_tasks2.get_hash()}")
print(f"tasks3 hash: {tb_tasks3.get_hash()}")
