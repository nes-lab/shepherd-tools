from typing import Optional

from pydantic import conint

from .. import ShpModel
from ..testbed import Firmware
from .virtual_source import VirtualSource


class TargetCfg(ShpModel):
    targetUIDs: list[str]
    customUIDs: list[conint(ge=0)]
    virtual_source: VirtualSource = VirtualSource(name="neutral")
    # ⤷ TODO should be callable by hash or name
    firmware1: Firmware
    firmware2: Optional[Firmware] = None
