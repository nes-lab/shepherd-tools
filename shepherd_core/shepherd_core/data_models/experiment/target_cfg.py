from typing import Optional

from pydantic import conint

from .. import ShpModel
from ..testbed import Firmware
from .virtual_source import VirtualSource


class TargetCfg(ShpModel, title="Config for Target Nodes (DuT)"):
    """ Test DocString Description
    """
    target_UIDs: list[str]
    custom_UIDs: list[conint(ge=0)]
    virtual_source: VirtualSource = VirtualSource(name="neutral")
    target_delays: list[conint(ge=0)]
    firmware1: Firmware
    firmware2: Optional[Firmware] = None
