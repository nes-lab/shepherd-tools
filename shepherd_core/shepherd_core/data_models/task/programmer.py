from pathlib import Path

from pydantic import confloat

from ..base.shepherd import ShpModel
from ..experiment.experiment import Experiment
from ..experiment.target_config import TargetConfig
from ..testbed.mcu import ProgrammerProtocol


class ProgrammerTask(ShpModel):
    firmware_file: Path
    sel_a: bool = True
    voltage: confloat(ge=2, lt=4) = 3
    datarate: int
    protocol: ProgrammerProtocol
    prog1: bool = True
    simulate: bool = False

    @classmethod
    def from_xp(cls, xp: Experiment, tcfg: TargetConfig, prog_port: int):
        fw = tcfg.firmware1 if prog_port == 1 else tcfg.firmware2
        if fw is None:
            return None

        pass
