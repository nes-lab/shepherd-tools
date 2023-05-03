from typing import Optional

from pydantic import conint
from pydantic import conlist
from pydantic import root_validator

from ..base.shepherd import ShpModel
from ..content.energy_environment import EnergyEnvironment
from ..content.firmware import Firmware
from ..content.virtual_source import VirtualSource
from ..testbed.target import Target
from ..testbed.target import id_int16
from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing


class TargetConfig(ShpModel, title="Target Config"):
    """Configuration for Target Nodes (DuT)"""

    target_IDs: conlist(item_type=id_int16, min_items=1, max_items=64)
    custom_IDs: Optional[conlist(item_type=id_int16, min_items=1, max_items=64)]
    # ⤷ will replace 'const uint16_t SHEPHERD_NODE_ID' in firmware

    energy_env: EnergyEnvironment  # alias: input
    virtual_source: VirtualSource = VirtualSource(name="neutral")
    target_delays: Optional[conlist(item_type=conint(ge=0), min_items=1, max_items=64)]
    # ⤷ individual starting times -> allows to use the same environment

    firmware1: Firmware
    firmware2: Optional[Firmware] = None

    power_tracing: Optional[PowerTracing]
    gpio_tracing: Optional[GpioTracing]
    gpio_actuation: Optional[GpioActuation]

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if not values["energy_env"].valid:
            raise ValueError(
                f"EnergyEnv '{values['energy_env'].name}' for target must be valid"
            )
        for _id in values["target_IDs"]:
            target = Target(id=_id)
            has_fw1 = values["firmware1"] is not None
            has_mcu1 = target.mcu1 is not None
            if has_fw1 and has_mcu1 and values["firmware1"].mcu.id != target.mcu1.id:
                raise ValueError(
                    f"Firmware1 for MCU of Target-ID '{target.id}' "
                    f"(={values['firmware1'].mcu.name}) "
                    f"is incompatible (={target.mcu1.name})"
                )

            has_fw2 = values["firmware2"] is not None
            has_mcu2 = target.mcu2 is not None
            if not has_fw2 and has_mcu2:
                fw_def = Firmware(name=target.mcu2.fw_name_default)
                # ⤷ this will raise if default is faulty
                if target.mcu2.id != fw_def.mcu.id:
                    raise ValueError(
                        f"Default-Firmware for MCU2 of Target-ID '{target.id}' "
                        f"(={fw_def.mcu.name}) "
                        f"is incompatible (={target.mcu2.name})"
                    )

            if has_fw2 and has_mcu2 and values["firmware2"].mcu.id != target.mcu2.id:
                raise ValueError(
                    f"Firmware2 for MCU of Target-ID '{target.id}' "
                    f"(={values['firmware2'].mcu.name}) "
                    f"is incompatible (={target.mcu2.name})"
                )
        c_ids = values["custom_IDs"]
        if c_ids is not None and (len(set(c_ids)) < len(set(values["target_IDs"]))):
            raise ValueError(
                f"Provided custom IDs {c_ids} not enough "
                f"to cover target range {values['target_IDs']}"
            )
        # TODO: if custom ids present, firmware must be ELF
        return values

    def get_custom_id(self, target_id: int):
        if target_id in self.target_IDs:
            return self.custom_IDs[self.target_IDs.index(target_id)]
        return None
