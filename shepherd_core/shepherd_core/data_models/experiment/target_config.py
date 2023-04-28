from typing import Optional

from pydantic import conint
from pydantic import conlist

from .. import ShpModel
from ..content import Firmware
from ..content.energy_environment import EnergyEnvironment
from ..content.virtual_source import VirtualSource
from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing


class TargetConfig(ShpModel, title="Target Config"):
    """Configuration for Target Nodes (DuT)"""

    target_UIDs: conlist(item_type=conint(ge=0, lt=2**16), min_items=1, max_items=64)
    custom_UIDs: Optional[
        conlist(item_type=conint(ge=0, lt=2**16), min_items=1, max_items=64)
    ]
    # ⤷ will replace 'const uint16_t SHEPHERD_NODE_ID' in firmware

    energy_env: EnergyEnvironment  # alias: input
    virtual_source: VirtualSource = VirtualSource(name="neutral")
    target_delays: Optional[conlist(item_type=conint(ge=0), min_items=1, max_items=64)]
    # ⤷ individual starting times -> allows to use the same environment

    firmware1: Firmware
    firmware2: Optional[Firmware] = None

    power_tracing: PowerTracing = PowerTracing()
    gpio_tracing: GpioTracing = GpioTracing()
    gpio_actuation: Optional[GpioActuation]
