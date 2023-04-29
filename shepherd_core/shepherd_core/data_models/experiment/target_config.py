from typing import Optional

from pydantic import conint
from pydantic import conlist
from pydantic import root_validator

from ..base.shepherd import ShpModel
from ..content.energy_environment import EnergyEnvironment
from ..content.firmware import Firmware
from ..content.virtual_source import VirtualSource
from ..testbed.mcu import MCU
from ..testbed.target import Target
from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing


class TargetConfig(ShpModel, title="Target Config"):
    """Configuration for Target Nodes (DuT)"""

    target_IDs: conlist(item_type=conint(ge=0, lt=2**16), min_items=1, max_items=64)
    custom_IDs: Optional[
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

    @root_validator(pre=False)
    def post_validation(cls, values: dict):
        for _id in values["target_IDs"]:
            target = Target(id=_id)
            has_fw1 = isinstance(values["firmware1"], Firmware)
            has_mcu1 = isinstance(target.mcu1, MCU)
            if has_fw1 and has_mcu1 and values["firmware1"].mcu.id != target.mcu1.id:
                raise ValueError(
                    f"Firmware1 for MCU of Target-ID '{target.id}' "
                    f"(={values['firmware1'].mcu.name}) "
                    f"is incompatible (={target.mcu1.name})"
                )

            has_fw2 = isinstance(values["firmware2"], Firmware)
            has_mcu2 = isinstance(target.mcu2, MCU)
            if not has_fw2 and has_mcu2:
                values["firmware2"] = Firmware(name=target.mcu2.fw_name_default)
                has_fw2 = isinstance(values["firmware2"], Firmware)
            if has_fw2 and has_mcu2 and values["firmware2"].mcu.id != target.mcu2.id:
                raise ValueError(
                    f"Firmware2 for MCU of Target-ID '{target.id}' "
                    f"(={values['firmware2'].mcu.name}) "
                    f"is incompatible (={target.mcu2.name})"
                )
        return values
