import copy
from pathlib import Path
from typing import Union

from pydantic import constr
from pydantic import root_validator
from pydantic import validate_arguments

from ...logger import logger
from ..base.shepherd import ShpModel
from ..content.firmware import FirmwareDType
from ..experiment.experiment import Experiment
from ..testbed.target import id_int16


class FirmwareModTask(ShpModel):
    """Config for Task that adds the custom ID to the firmware & stores it into a file"""

    data: Union[constr(min_length=3, max_length=1_000_000), Path]
    data_type: FirmwareDType
    custom_id: id_int16
    firmware_file: Path

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if values["data_type"] in [FirmwareDType.base64_hex, FirmwareDType.path_hex]:
            logger.warning(
                "Firmware is scheduled to get custom-ID but is not in elf-format"
            )
        return values

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment, tgt_id: int, prog_port: int, fw_path: Path):
        tgt_cfg = xp.get_target_config(tgt_id)

        fw = tgt_cfg.firmware1 if prog_port == 1 else tgt_cfg.firmware2
        if (fw is None) or (tgt_cfg.get_custom_id(tgt_id) is None):
            return None

        return cls(
            data=fw.data,
            data_type=fw.data_type,
            custom_id=tgt_cfg.get_custom_id(tgt_id),
            firmware_file=copy.copy(fw_path),
        )
