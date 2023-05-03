from pathlib import Path

from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models.task.emulation import EmulationTask
from shepherd_core.data_models.task.firmware_mod import FirmwareModTask
from shepherd_core.data_models.task.programmer import ProgrammerTask
from shepherd_core.data_models.testbed import ProgrammerProtocol


def test_task_model_min_emu():
    EmulationTask(
        input_path="./here",
    )


def test_task_model_min_fw():
    FirmwareModTask(
        data=Path("/"),
        data_type=FirmwareDType.path_elf,
        custom_id=42,
        firmware_file=Path("fw_to_be.elf"),
    )


def test_task_model_min_prog():
    ProgrammerTask(
        firmware_file=Path("fw_to_load.hex"),
        protocol=ProgrammerProtocol.SWD,
    )
