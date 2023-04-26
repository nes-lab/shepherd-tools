from typing import Optional

from .. import ShpModel
from ..testbed import Firmware
from .virtual_source import VirtualSource


class TargetCfg(ShpModel):
    targetUIDs: list[str]
    customUIDs: list[int]
    virtual_source: VirtualSource = VirtualSource(name="neutral")
    # ⤷ TODO should be callable by hash or name
    firmware1: Firmware
    firmware2: Optional[Firmware] = None
