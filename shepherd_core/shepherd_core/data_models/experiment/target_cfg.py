from typing import Optional

from pydantic import conint

from .. import ShpModel
from ..testbed import Firmware
from . import Emulator
from .virtual_source import VirtualSource


class TargetCfg(ShpModel, title="Target Config"):
    """Configuration for Target Nodes (DuT)"""

    target_UIDs: list[conint(ge=0, lt=2**16)]
    custom_UIDs: list[conint(ge=0, lt=2**16)] = []
    # ⤷ will replace 'const uint16_t SHEPHERD_NODE_ID'

    emulator: Emulator = VirtualSource(name="neutral")
    target_delays: list[conint(ge=0)] = []
    firmware1: Firmware
    firmware2: Optional[Firmware] = None
