from pathlib import Path

import pytest

from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models.task.emulation import EmulationTask
from shepherd_core.data_models.task.firmware_mod import FirmwareModTask
from shepherd_core.data_models.task.harvest import HarvestTask
from shepherd_core.data_models.task.programming import ProgrammingTask
from shepherd_core.data_models.testbed import ProgrammerProtocol


def test_task_model_emu_min() -> None:
    EmulationTask(
        input_path="./here",
    )


def test_task_model_emu_fault_in_past() -> None:
    with pytest.raises(ValueError):
        EmulationTask(
            input_path="./here",
            time_start="1984-01-01 11:12:13",
        )


@pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 4.5, "buffer", "main"])
def test_task_model_emu_custom_aux(value) -> None:
    EmulationTask(
        input_path="./here",
        voltage_aux=value,
    )


@pytest.mark.parametrize("value", [-1.0, 5, "max", "something"])
def test_task_model_emu_fault_aux(value) -> None:
    with pytest.raises(ValueError):
        EmulationTask(
            input_path="./here",
            voltage_aux=value,
        )


def test_task_model_fw_min() -> None:
    FirmwareModTask(
        data=Path("/"),
        data_type=FirmwareDType.path_elf,
        custom_id=42,
        firmware_file=Path("fw_to_be.elf"),
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
    assert hrv.duration.seconds == 42


def test_task_model_hrv_too_late() -> None:
    with pytest.raises(ValueError):
        HarvestTask(
            output_path="./here",
            time_start="1984-01-01 11:12:13",
        )


def test_task_model_prog_min() -> None:
    ProgrammingTask(
        firmware_file=Path("fw_to_load.hex"),
        protocol=ProgrammerProtocol.SWD,
        mcu_type="nrf52",
    )
