from pathlib import Path
from typing import Union

import pytest
from pydantic import ValidationError

from shepherd_core.data_models import Experiment
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioActuation
from shepherd_core.data_models import GpioEvent
from shepherd_core.data_models.task import ObserverTasks
from shepherd_core.data_models.task.emulation import EmulationTask
from shepherd_core.data_models.task.firmware_mod import FirmwareModTask
from shepherd_core.data_models.task.harvest import HarvestTask
from shepherd_core.data_models.task.programming import ProgrammingTask
from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import Testbed as TasteBad


def test_task_model_emu_min() -> None:
    EmulationTask(
        input_path="./here",
    )


def test_task_model_emu_fault_in_past() -> None:
    with pytest.raises(ValidationError):
        EmulationTask(
            input_path="./here",
            time_start="1984-01-01 11:12:13",
        )


@pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 4.5, "buffer", "main"])
def test_task_model_emu_custom_aux(value: Union[float, str]) -> None:
    EmulationTask(
        input_path="./here",
        voltage_aux=value,
    )


@pytest.mark.parametrize("value", [-1.0, 5, "max", "something"])
def test_task_model_emu_fault_aux(value: Union[float, str]) -> None:
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


def test_task_model_hrv_too_late() -> None:
    with pytest.raises(ValidationError):
        HarvestTask(
            output_path="./here",
            time_start="1984-01-01 11:12:13",
        )


def test_task_model_observer_min1() -> None:
    ObserverTasks(
        observer="peeping tom",
        owner_id=666,
        time_prep="2044-01-01 12:13:14",
        root_path="/usr",
        abort_on_error=False,
    )


def test_task_model_observer_min2() -> None:
    path = Path(__file__).with_name("example_config_experiment.yaml")
    xp = Experiment.from_file(path)
    ObserverTasks.from_xp(xp=xp, tb=TasteBad(name="shepherd_tud_nes"), tgt_id=1)


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
