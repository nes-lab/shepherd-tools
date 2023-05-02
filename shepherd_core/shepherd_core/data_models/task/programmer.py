from pathlib import Path

from pydantic import confloat
from pydantic import conint
from pydantic import validate_arguments

from shepherd_core.data_models import Experiment
from shepherd_core.data_models.testbed import TargetPort
from shepherd_core.data_models.testbed import Testbed

from ..base.shepherd import ShpModel
from ..testbed.mcu import ProgrammerProtocol


class ProgrammerTask(ShpModel):
    firmware_file: Path
    sel_a: bool = True
    voltage: confloat(ge=1, lt=5) = 3
    datarate: conint(gt=0, le=1_000_000) = 500_000
    protocol: ProgrammerProtocol
    prog1: bool = True
    simulate: bool = False

    @classmethod
    @validate_arguments
    def from_xp(
        cls, xp: Experiment, tb: Testbed, tgt_id: int, prog_port: int, fw_path: Path
    ):
        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)

        fw = tgt_cfg.firmware1 if prog_port == 1 else tgt_cfg.firmware2
        if fw is None:
            return None

        return ProgrammerTask(
            firmware_file=fw_path,
            sel_a=obs.get_target_port(tgt_id) == TargetPort.A,
            voltage=fw.mcu.prog_voltage,
            datarate=fw.mcu.prog_datarate,
            protocol=fw.mcu.prog_protocol,
            prog1=prog_port == 1,
        )
