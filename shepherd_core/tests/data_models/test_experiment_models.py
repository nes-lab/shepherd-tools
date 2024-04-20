from datetime import timedelta

import pytest
from pydantic import ValidationError

from shepherd_core import local_now
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models import VirtualSourceConfig
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


def test_experiment_model_exp_min() -> None:
    Experiment(
        name="mex per",
        target_configs=[
            TargetConfig(
                target_IDs=[1],
                energy_env=EnergyEnvironment(name="SolarSunny"),
                firmware1=Firmware(name="nrf52_demo_rf"),
            )
        ],
    )


def test_experiment_model_exp_yaml_load() -> None:
    exp1_data = load_yaml("example_config_experiment_alternative.yaml")
    Experiment(**exp1_data)


def test_experiment_model_exp_yaml_comparison() -> None:
    exp1_data = load_yaml("example_config_experiment_alternative.yaml")
    exp1 = Experiment(**exp1_data)

    target_cfgs = TargetConfig(
        target_IDs=list(range(1, 5)),
        custom_IDs=list(range(4)),
        energy_env={"name": "SolarSunny"},
        virtual_source={"name": "diode+capacitor"},
        firmware1={"name": "nrf52_demo_rf"},
    )
    exp2 = Experiment(
        id=4567,
        name="meaningful Test-Name",
        created="2023-11-11 11:11:11",
        time_start="2033-12-12 12:12:12",
        target_configs=[target_cfgs],
    )
    assert exp1.model_dump() == exp2.model_dump()
    assert exp1.get_hash() == exp2.get_hash()


def test_experiment_model_exp_collision_target_id() -> None:
    hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")
    target_cfgs = [
        TargetConfig(
            target_IDs=[1, 2, 3],  # <- collision
            custom_IDs=[0, 1, 2, 3],
            energy_env={"name": "SolarSunny"},
            virtual_source={"name": "diode+capacitor"},
            firmware1={"name": "nrf52_demo_rf"},
        ),
        TargetConfig(
            target_IDs=list(range(1, 5)),  # <- collision
            custom_IDs=list(range(7, 18)),  # note: longer list is OK
            energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
            virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="msp430_deep_sleep"),
        ),
    ]
    with pytest.raises(ValidationError):
        _ = Experiment(
            id="4567",
            name="meaningful Test-Name",
            time_start=local_now() + timedelta(minutes=30),
            target_configs=target_cfgs,
        )


def test_experiment_model_exp_collision_custom_id() -> None:
    hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")
    target_cfgs = [
        TargetConfig(
            target_IDs=[1, 2, 3],
            custom_IDs=[0, 1, 7],  # <- collision
            energy_env={"name": "SolarSunny"},
            virtual_source={"name": "diode+capacitor"},
            firmware1={"name": "nrf52_demo_rf"},
        ),
        TargetConfig(
            target_IDs=list(range(1, 5)),
            custom_IDs=list(range(7, 18)),  # <- collision
            energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
            virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="msp430_deep_sleep"),
        ),
    ]
    with pytest.raises(ValidationError):
        _ = Experiment(
            id="4567",
            name="meaningful Test-Name",
            time_start=local_now() + timedelta(minutes=30),
            target_configs=target_cfgs,
        )


def test_experiment_model_exp_collision_observer() -> None:
    hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")
    target_cfgs = [
        TargetConfig(
            target_IDs=[1, 1001],  # <- both on same observer
            custom_IDs=list(range(7, 18)),
            energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
            virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="msp430_deep_sleep"),
        ),
    ]
    with pytest.raises(ValidationError):
        _ = Experiment(
            id="4567",
            name="meaningful Test-Name",
            time_start=local_now() + timedelta(minutes=30),
            target_configs=target_cfgs,
        )


def test_experiment_model_exp_missing_target() -> None:
    hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")
    with pytest.raises(ValidationError):
        # should raise ValueError in Experiment
        # buts gets already caught in target_config
        _ = [
            TargetConfig(
                target_IDs=[1234567],  # <- not existent
                custom_IDs=list(range(7, 18)),
                energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
                virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
                firmware1=Firmware(name="nrf52_demo_rf"),
                firmware2=Firmware(name="msp430_deep_sleep"),
            ),
        ]
        # experiment (like above) removed


def test_experiment_model_pwrtracing_min() -> None:
    PowerTracing()


def test_experiment_model_pwrtracing_fault_post() -> None:
    with pytest.raises(NotImplementedError):
        PowerTracing(calculate_power=True)


def test_experiment_model_pwrtracing_fault_discard_all() -> None:
    with pytest.raises(ValidationError):
        PowerTracing(calculate_power=False, discard_current=True, discard_voltage=True)


def test_experiment_model_gpiotracing_min() -> None:
    GpioTracing()


def test_experiment_model_gpiotracing_fault_mask() -> None:
    with pytest.raises(ValidationError):
        GpioTracing(mask=0)


def test_experiment_model_gpioevent_min() -> None:
    gevt = GpioEvent(
        delay=300,
        gpio=GPIO(name="GPIO3"),
        level=GpioLevel.high,
    )
    gevt.get_events()


def test_experiment_model_gpioevent_fault_readonly() -> None:
    with pytest.raises(ValidationError):
        GpioEvent(
            delay=300,
            gpio=GPIO(name="BAT_OK"),
            level=GpioLevel.high,
        )


def test_experiment_model_gpioactuation_min() -> None:
    gact = GpioActuation(
        events=[
            GpioEvent(
                delay=300,
                gpio=GPIO(name="GPIO2"),
                level=GpioLevel.high,
            )
        ]
    )
    gact.get_gpios()


def test_experiment_model_syslogging_min() -> None:
    SystemLogging()


def test_experiment_model_tgt_cfg_min1() -> None:
    cfg = TargetConfig(
        target_IDs=[1],
        energy_env=EnergyEnvironment(name="SolarSunny"),
        firmware1=Firmware(name="nrf52_demo_rf"),
    )
    for _id in cfg.target_IDs:
        Target(id=_id)
    assert cfg.get_custom_id(1) is None


def test_experiment_model_tgt_cfg_min2() -> None:
    cfg = TargetConfig(
        target_IDs=[1, 2],
        custom_IDs=[7, 9],
        energy_env=EnergyEnvironment(name="SolarSunny"),
        firmware1=Firmware(name="nrf52_demo_rf"),
    )
    for _id in cfg.target_IDs:
        Target(id=_id)
    assert cfg.get_custom_id(1) == 7
    assert cfg.get_custom_id(2) == 9
    assert cfg.get_custom_id(3) is None


def test_experiment_model_tgt_cfg_fault_valid_ee() -> None:
    with pytest.raises(ValidationError):
        _ = TargetConfig(
            target_IDs=[1],
            energy_env=EnergyEnvironment(name="nuclear"),
            firmware1=Firmware(name="nrf52_demo_rf"),
        )


def test_experiment_model_tgt_cfg_fault_firmware1() -> None:
    with pytest.raises(ValidationError):
        _ = TargetConfig(
            target_IDs=[1],  # is nRF
            energy_env=EnergyEnvironment(name="SolarSunny"),
            firmware1=Firmware(name="msp430_spi_fram"),
        )


def test_experiment_model_tgt_cfg_fault_firmware2() -> None:
    with pytest.raises(ValidationError):
        _ = TargetConfig(
            target_IDs=[1],  # is nRF
            energy_env=EnergyEnvironment(name="SolarSunny"),
            firmware1=Firmware(name="nrf52_demo_rf"),
            firmware2=Firmware(name="nrf52_demo_rf"),
        )


def test_experiment_model_tgt_cfg_fault_custom_ids() -> None:
    with pytest.raises(ValidationError):
        _ = TargetConfig(
            target_IDs=[1, 2, 3],
            custom_IDs=[0, 1],  # not enough
            energy_env=EnergyEnvironment(name="SolarSunny"),
            firmware1=Firmware(name="nrf52_demo_rf"),
        )
