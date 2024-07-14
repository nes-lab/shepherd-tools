"""Shows different ways to define an experiment.

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

from shepherd_core import WebClient
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualHarvesterConfig
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks

# generate description for all parameters -> base for web-forms
Experiment.schema_to_file("experiment_schema.yaml")

# For online-queries the lib can be connected to the testbed-server.
# NOTE: there are 3 states:
# - unconnected -> demo-fixtures are queried (locally)
# - connected -> publicly available data is queried online
# - logged in with valid token -> also private data is queried online
do_connect = False
if do_connect:
    WebClient()

# Defining an Experiment in Python
hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")

target_cfgs = [
    # first Instance similar to yaml-syntax
    TargetConfig(
        target_IDs=[9, 10, 11],
        custom_IDs=[0, 1, 2],
        energy_env={"name": "SolarSunny"},
        virtual_source={"name": "diode+capacitor"},
        firmware1={"name": "nrf52_demo_rf"},
    ),
    # second Instance fully object-oriented (recommended)
    TargetConfig(
        target_IDs=list(range(1, 5)),
        custom_IDs=list(range(7, 18)),  # note: longer list is OK
        energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
        virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
        firmware1=Firmware(name="nrf52_demo_rf"),
        firmware2=Firmware(name="msp430_deep_sleep"),
    ),
]

xperi1 = Experiment(
    id="4567",
    name="meaningful Test-Name",
    time_start="2033-03-13 14:15:16",  # or: datetime.now() + timedelta(minutes=30)
    target_configs=target_cfgs,
)

# Safe, reload and compare content
xperi1.to_file("experiment_from_py.yaml", minimal=False)
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
