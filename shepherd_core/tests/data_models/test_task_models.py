from pathlib import Path

import pytest
import shepherd_core.data_models as sdm
from pydantic import ValidationError
from shepherd_core.config import config
from shepherd_core.data_models import Experiment
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioActuation
from shepherd_core.data_models import GpioEvent
from shepherd_core.data_models.task import ObserverTasks
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.task.emulation import EmulationTask
from shepherd_core.data_models.task.firmware_mod import FirmwareModTask
from shepherd_core.data_models.task.harvest import HarvestTask
from shepherd_core.data_models.task.programming import ProgrammingTask
from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import Testbed as TasteBad

from shepherd_core import fw_tools


def test_task_model_emu_min() -> None:
    EmulationTask(
        input_path="./here",
    )


@pytest.mark.skip(reason="Relaxed in v2025.08.01")
def test_task_model_emu_fault_in_past() -> None:
    with pytest.raises(ValidationError):
        EmulationTask(
            input_path="./here",
            time_start="1984-01-01 11:12:13",
        )


@pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 4.5, "buffer", "main"])
def test_task_model_emu_custom_aux(value: float | str) -> None:
    EmulationTask(
        input_path="./here",
        voltage_aux=value,
    )


@pytest.mark.parametrize("value", [-1.0, 5, "max", "something"])
def test_task_model_emu_fault_aux(value: float | str) -> None:
    with pytest.raises(ValidationError):
        EmulationTask(
            input_path="./here",
            voltage_aux=value,
        )


def test_task_model_emu_fault_gpio_actuation() -> None:
    with pytest.raises(ValidationError):
        EmulationTask(
            input_path="./here",
            gpio_actuation=GpioActuation(
                events=[GpioEvent(delay=5, gpio=GPIO(name="GPIO5"))],
            ),
        )


def test_task_model_fw_min() -> None:
    FirmwareModTask(
        data=Path("/"),
        data_type=FirmwareDType.path_elf,
        custom_id=42,
        firmware_file=Path("fw_to_be.elf"),
    )


def test_task_model_fw_fault_hex() -> None:
    # just a warning for now
    FirmwareModTask(
        data=Path("/"),
        data_type=FirmwareDType.path_hex,
        custom_id=42,
        firmware_file=Path("fw_to_be.hex"),
    )


def test_task_model_hrv_min() -> None:
    HarvestTask(
        output_path="./here",
    )


def test_task_model_hrv_duration() -> None:
    hrv = HarvestTask(
        output_path="./here",
        duration=42,
    )
    assert hrv.duration.total_seconds() == 42


@pytest.mark.skip(reason="Relaxed in v2025.08.01")
def test_task_model_hrv_too_late() -> None:
    with pytest.raises(ValidationError):
        HarvestTask(
            output_path="./here",
            time_start="1984-01-01 11:12:13",
        )


def test_task_model_observer_min1() -> None:
    ObserverTasks(
        observer="peeping tom",
        time_prep="2044-01-01 12:13:14",
        root_path="/usr",
    )


def test_task_model_observer_min2() -> None:
    path = Path(__file__).with_name("example_config_experiment.yaml")
    exp = Experiment.from_file(path)
    ObserverTasks.from_xp(xp=exp, xp_folder=None, tb=TasteBad(name="shepherd_tud_nes"), tgt_id=1)


def test_task_model_prog_min() -> None:
    ProgrammingTask(
        firmware_file=Path("fw_to_load.hex"),
        protocol=ProgrammerProtocol.SWD,
        mcu_type="nrf52",
    )


def test_task_model_prog_fault_elf() -> None:
    with pytest.raises(ValidationError):
        ProgrammingTask(
            firmware_file=Path("fw_to_load.elf"),
            protocol=ProgrammerProtocol.SWD,
            mcu_type="nrf52",
        )


def test_tasks_are_contained() -> None:
    config.TESTBED = "unit_testing_testbed"
    firmware_path = Path(__file__).parent.parent / "fw_tools/build_nrf.elf"
    tgt_cfg = sdm.TargetConfig(
        target_IDs=[42],
        energy_env=sdm.EnergyEnvironment(name="synthetic_static_3000mV_50mA"),
        firmware1=sdm.Firmware(
            name="FW_TestXYZ",
            data=fw_tools.file_to_base64(firmware_path),
            data_type=FirmwareDType.base64_elf,
            data_2_copy=False,
            mcu=MCU(name="nRF52"),
        ),
        power_tracing=None,
        uart_logging=sdm.UartLogging(baudrate=115_200),
        gpio_tracing=sdm.GpioTracing(),
    )
    xp = Experiment(
        name="test-experiment",
        duration=30,
        target_configs=[tgt_cfg],
    )
    tb = TasteBad()
    tb_tasks = TestbedTasks.from_xp(xp, tb)
    paths_allowed = config.PATHS_ALLOWED
    for obs_tasks in tb_tasks.observer_tasks:
        assert obs_tasks.is_contained(paths_allowed)
    assert tb_tasks.is_contained()
