from datetime import datetime
from datetime import timedelta

from shepherd_core.data_models.experiment import Emulator
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.testbed import Target

Experiment.dump_schema("experiment_schema.yaml")

time_start = datetime.utcnow() + timedelta(minutes=30)

emu = Emulator(input_path="solar_xyz")

targets = [
    Target(name="T_nRF52_2021_001", firmware1={"name": "nrf52_testable"}),
    Target(name="T_nRF52_FRAM_2023_001", firmware1={"name": "nrf52_demo_rf"}),
    Target(uid="3003", firmware1={"name": "nrf52_demo_rf"}),
]

xperi = Experiment(
    name="meaningful Test-Name",
    output_path="f_out.h5",
    emulator_default=emu,
    time_start=time_start,
    targets=targets,
)

xperi.dump_dict("experiment_dict.yaml")
