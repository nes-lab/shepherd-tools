from typing import Optional

from pydantic import conint
from pydantic import conlist
from pydantic import root_validator

from ..base.content import IdInt
from ..base.shepherd import ShpModel
from ..content.energy_environment import EnergyEnvironment
from ..content.firmware import Firmware
from ..content.virtual_source import VirtualSourceConfig
from ..testbed.target import IdInt16
from ..testbed.target import Target
from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing


class TargetConfig(ShpModel, title="Target Config"):
    """Configuration for Target Nodes (DuT)"""

    target_IDs: conlist(item_type=IdInt, min_items=1, max_items=64)
    custom_IDs: Optional[conlist(item_type=IdInt16, min_items=1, max_items=64)]
    # ⤷ will replace 'const uint16_t SHEPHERD_NODE_ID' in firmware

    energy_env: EnergyEnvironment  # alias: input
    virtual_source: VirtualSourceConfig = VirtualSourceConfig(name="neutral")
    target_delays: Optional[conlist(item_type=conint(ge=0), min_items=1, max_items=64)]
    # ⤷ individual starting times -> allows to use the same environment

    firmware1: Firmware
    firmware2: Optional[Firmware] = None

    power_tracing: Optional[PowerTracing]
    gpio_tracing: Optional[GpioTracing]
    gpio_actuation: Optional[GpioActuation]

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if not values.get("energy_env").valid:
            raise ValueError(
                f"EnergyEnv '{values['energy_env'].name}' for target must be valid"
            )
        for _id in values.get("target_IDs"):
            target = Target(id=_id)
            for mcu_num in [1, 2]:
                val_fw = values.get(f"firmware{mcu_num}")
                has_fw = val_fw is not None
                tgt_mcu = target[f"mcu{mcu_num}"]
                has_mcu = tgt_mcu is not None
                if not has_fw and has_mcu:
                    fw_def = Firmware(name=tgt_mcu.fw_name_default)
                    # ⤷ this will raise if default is faulty
                    if tgt_mcu.id != fw_def.mcu.id:
                        raise ValueError(
                            f"Default-Firmware for MCU{mcu_num} of Target-ID '{target.id}' "
                            f"(={fw_def.mcu.name}) "
                            f"is incompatible (={tgt_mcu.name})"
                        )
                if has_fw and has_mcu and val_fw.mcu.id != tgt_mcu.id:
                    raise ValueError(
                        f"Firmware{mcu_num} for MCU of Target-ID '{target.id}' "
                        f"(={val_fw.mcu.name}) "
                        f"is incompatible (={tgt_mcu.name})"
                    )

        c_ids = values.get("custom_IDs")
        t_ids = values.get("target_IDs")
        if c_ids is not None and (len(set(c_ids)) < len(set(t_ids))):
            raise ValueError(
                f"Provided custom IDs {c_ids} not enough "
                f"to cover target range {t_ids}"
            )
        # TODO: if custom ids present, firmware must be ELF
        return values

    def get_custom_id(self, target_id: int) -> Optional[int]:
        if self.custom_IDs is not None and target_id in self.target_IDs:
            return self.custom_IDs[self.target_IDs.index(target_id)]
        return None
