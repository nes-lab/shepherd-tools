from pathlib import Path
from typing import Optional

from pydantic import confloat
from pydantic import conint

from ..base.shepherd import ShpModel
from ..testbed.mcu import ProgrammerProtocol
from .experiment import Experiment


class ProgrammerConfig(ShpModel):
    firmware_file: Path
    sel_a: bool = True
    voltage: confloat(ge=2, lt=4) = 3
    datarate: int
    protocol: ProgrammerProtocol
    prog1: bool = True
    simulate: bool = False
    custom_id: Optional[conint(ge=0, lt=2**16)]

    @classmethod
    def from_xp(cls, xp: Experiment):
        pass
