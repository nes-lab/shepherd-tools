import copy
from pathlib import Path

from pydantic import confloat
from pydantic import conint
from pydantic import root_validator
from pydantic import validate_arguments

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
    voltage: confloat(ge=1, lt=5) = 3
    datarate: conint(gt=0, le=1_000_000) = 500_000
    protocol: ProgrammerProtocol

    simulate: bool = False

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if values.get("firmware_file").suffix.lower() != ".hex":
            ValueError(f"Firmware is not intel-.hex ('{values['firmware_file']}')")
        return values

    @classmethod
    @validate_arguments
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
