from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import GpioActuation
from shepherd_core.data_models.experiment import GpioEvent
from shepherd_core.data_models.experiment import GpioLevel
from shepherd_core.data_models.experiment import GpioTracing
from shepherd_core.data_models.experiment import ObserverEmulationConfig
from shepherd_core.data_models.experiment import PowerTracing
from shepherd_core.data_models.experiment import SystemLogging
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.testbed import GPIO


def test_experiment_model_min_exp():
    Experiment(
        name="mex per",
        target_configs=[
            TargetConfig(
                target_UIDs=[3001],
                energy_env=EnergyEnvironment(name="SolarSunny"),
                firmware1=Firmware(name="nrf52_demo_rf"),
            )
        ],
    )


def test_experiment_model_min_observer():
    ObserverEmulationConfig(
        input_path="./here",
    )


def test_experiment_model_min_pwrtracing():
    PowerTracing()


def test_experiment_model_min_gpiotracing():
    GpioTracing()


def test_experiment_model_min_gpioevent():
    GpioEvent(
        delay=300,
        gpio=GPIO(name="GPIO7"),
        level=GpioLevel.high,
    )


def test_experiment_model_min_gpioactuation():
    GpioActuation(
        events=[
            GpioEvent(
                delay=300,
                gpio=GPIO(name="GPIO7"),
                level=GpioLevel.high,
            )
        ]
    )


def test_experiment_model_min_syslogging():
    SystemLogging()
