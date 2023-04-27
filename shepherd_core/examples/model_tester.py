from datetime import datetime
from datetime import timedelta

from shepherd_core.data_models.experiment import Emulator
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetCfg
from shepherd_core.data_models.experiment import VirtualHarvester
from shepherd_core.data_models.experiment import VirtualSource

Experiment.dump_schema("experiment_schema.yaml")

hrv1 = VirtualHarvester(name="mppt_opt")
src1 = VirtualSource(name="diode+capacitor", harvester=hrv1)
emu1 = Emulator(input_path="solar_xyz", virtual_source=src1)

hrv2 = VirtualHarvester(name="mppt_bq_thermoelectric")
src2 = VirtualSource(name="BQ25570-Schmitt", harvester=hrv2)
emu2 = Emulator(input_path="thermo_xyz", virtual_source=src2)

target_configs = [
    TargetCfg(
        target_UIDs=list(range(3001, 3004)),
        custom_UIDs=list(range(0, 3)),
        emulator=emu1,
        firmware1={"name": "nrf52_demo_rf"},
    ),
    TargetCfg(
        target_UIDs=list(range(2001, 2005)),
        custom_UIDs=list(range(0, 4)),
        emulator=emu2,
        firmware1={"name": "nrf52_demo_rf"},
        firmware2={"name": "msp430_deep_sleep"},
    ),
]

xperi = Experiment(
    name="meaningful Test-Name",
    output_path="f_out.h5",
    time_start=datetime.utcnow() + timedelta(minutes=30),
    target_cfgs=target_configs,
)

xperi.dump_dict("experiment_dict.yaml")
