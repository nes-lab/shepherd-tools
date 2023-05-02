import hashlib

from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import GpioActuation
from shepherd_core.data_models.experiment import GpioEvent
from shepherd_core.data_models.experiment import GpioLevel
from shepherd_core.data_models.experiment import GpioTracing
from shepherd_core.data_models.experiment import PowerTracing
from shepherd_core.data_models.experiment import SystemLogging
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import Target

from .conftest import load_yaml


def test_experiment_model_min_tgt_cfg():
    cfg = TargetConfig(
        target_IDs=[3001],
        energy_env=EnergyEnvironment(name="SolarSunny"),
        firmware1=Firmware(name="nrf52_demo_rf"),
    )
    for _id in cfg.target_IDs:
        Target(id=_id)


def test_experiment_model_min_exp():
    Experiment(
        name="mex per",
        target_configs=[
            TargetConfig(
                target_IDs=[3001],
                energy_env=EnergyEnvironment(name="SolarSunny"),
                firmware1=Firmware(name="nrf52_demo_rf"),
            )
        ],
    )


def test_experiment_model_yaml_load():
    exp1_data = load_yaml("example_config_experiment_alternative.yaml")
    Experiment(**exp1_data)


def test_experiment_model_yaml_comparison():
    exp1_data = load_yaml("example_config_experiment_alternative.yaml")
    exp1 = Experiment(**exp1_data)
    exp1_hash = hashlib.sha3_224(str(exp1.dict()).encode("utf-8")).hexdigest()
    print(f"YamlExp Hash {exp1_hash}")

    target_cfgs = TargetConfig(
        target_IDs=list(range(2001, 2005)),
        custom_IDs=list(range(0, 4)),
        energy_env={"name": "SolarSunny"},
        virtual_source={"name": "diode+capacitor"},
        firmware1={"name": "nrf52_demo_rf"},
    )
    exp2 = Experiment(
        id=4567,
        name="meaningful Test-Name",
        created="2023-11-11 11:11:11",
        time_start="2023-12-12 12:12:12",
        target_configs=[target_cfgs],
    )
    exp2_hash = hashlib.sha3_224(str(exp2.dict()).encode("utf-8")).hexdigest()
    print(f"  PyExp Hash {exp2_hash}")
    assert exp1_hash == exp2_hash


def test_experiment_model_min_pwrtracing():
    PowerTracing()


def test_experiment_model_min_gpiotracing():
    GpioTracing()


def test_experiment_model_min_gpioevent():
    GpioEvent(
        delay=300,
        gpio=GPIO(name="GPIO3"),
        level=GpioLevel.high,
    )


def test_experiment_model_min_gpioactuation():
    GpioActuation(
        events=[
            GpioEvent(
                delay=300,
                gpio=GPIO(name="GPIO2"),
                level=GpioLevel.high,
            )
        ]
    )


def test_experiment_model_min_syslogging():
    SystemLogging()
