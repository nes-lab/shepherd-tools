import copy
from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic import validate_call
from typing_extensions import Annotated

from ..base.content import IdInt
from ..base.content import SafeStr
from ..base.shepherd import ShpModel
from ..experiment.experiment import Experiment
from ..testbed.cape import TargetPort
from ..testbed.mcu import ProgrammerProtocol
from ..testbed.target import MCUPort
from ..testbed.testbed import Testbed


class ProgrammingTask(ShpModel):
    """Config for Task programming the target selected"""

    firmware_file: Path
    target_port: TargetPort = TargetPort.A
    mcu_port: MCUPort = 1
    mcu_type: SafeStr
    # ⤷ for later
    voltage: Annotated[float, Field(ge=1, lt=5)] = 3
    datarate: Annotated[int, Field(gt=0, le=1_000_000)] = 500_000
    protocol: ProgrammerProtocol

    simulate: bool = False

    verbose: Annotated[int, Field(ge=0, le=4)] = 2
    # ⤷ 0=Errors, 1=Warnings, 2=Info, 3=Debug

    @model_validator(mode="after")
    def post_validation(self):
        if self.firmware_file.suffix.lower() != ".hex":
            ValueError(f"Firmware is not intel-.hex ('{self.firmware_file}')")
        return self

    @classmethod
    @validate_call
    def from_xp(
        cls,
        xp: Experiment,
        tb: Testbed,
        tgt_id: IdInt,
        mcu_port: MCUPort,
        fw_path: Path,
    ):
        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)

        fw = tgt_cfg.firmware1 if mcu_port == 1 else tgt_cfg.firmware2
        if fw is None:
            return None

        return cls(
            firmware_file=copy.copy(fw_path),
            target_port=obs.get_target_port(tgt_id),
            mcu_port=mcu_port,
            mcu_type=fw.mcu.name,
            voltage=fw.mcu.prog_voltage,
            datarate=fw.mcu.prog_datarate,
            protocol=fw.mcu.prog_protocol,
        )
