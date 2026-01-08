"""Configuration related to Target Nodes (DuT)."""

from pathlib import Path
from typing import Annotated
from typing import final

from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.data_models.base.content import IdInt
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.content.energy_environment import EnergyEnvironment
from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.data_models.content.virtual_source_config import VirtualSourceConfig
from shepherd_core.data_models.testbed.target import IdInt16
from shepherd_core.data_models.testbed.target import Target
from shepherd_core.logger import log

from .observer_features import GpioActuation
from .observer_features import GpioTracing
from .observer_features import PowerTracing
from .observer_features import UartLogging

# defaults (pre-init complex types)
vsrc_neutral = VirtualSourceConfig(name="neutral")


@final
class TargetConfig(ShpModel):
    """Configuration related to Target Nodes (DuT)."""

    target_IDs: Annotated[list[IdInt], Field(min_length=1, max_length=128)]
    custom_IDs: Annotated[list[IdInt16], Field(min_length=1, max_length=128)] | None = None
    """ ⤷ custom ID will replace 'const uint16_t SHEPHERD_NODE_ID' in firmware.

    if no custom ID is provided, the original ID of target is used
    """

    energy_env: EnergyEnvironment
    """ input for the virtual source """
    virtual_source: VirtualSourceConfig = vsrc_neutral
    target_delays: (
        Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1, max_length=128)] | None
    ) = None
    """ ⤷ individual starting times

    - allows to use the same environment
    - not implemented ATM
    """

    firmware1: Firmware
    """ ⤷ omitted FW gets set to neutral deep-sleep"""
    firmware2: Firmware | None = None
    """ ⤷ omitted FW gets set to neutral deep-sleep"""

    power_tracing: PowerTracing | None = None
    gpio_tracing: GpioTracing | None = None
    gpio_actuation: GpioActuation | None = None
    uart_logging: UartLogging | None = None

    @model_validator(mode="after")
    def validate_eenv_mapping(self) -> Self:
        """Validate that a mapping between targets and EEnvs can be found."""
        if self.energy_env.repetitions_ok:
            return self
        n_env = len(self.energy_env)
        n_tgt = len(self.target_IDs)
        if n_env == n_tgt:
            return self
        if n_env > n_tgt:
            log.debug(
                f"TargetConfig for {self.target_IDs} has remaining "
                f"{n_env - n_tgt} EEnv-profiles -> will not be used there"
            )
            return self
        msg = (
            f"Energy-Environment of TargetConfig for tgt{self.target_IDs} was too small "
            f"({n_tgt - n_env} missing). Please use a larger environment."
        )
        raise ValueError(msg)

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        try:
            self.energy_env.enforce_validity()
        except ValueError as xpt:
            msg = f"EnergyEnv '{self.energy_env.name}' for TargetConfig must be valid.\n{xpt}"
            # note: added xpt in text because pydantic refuses to show "from xpt" part below
            raise ValueError(msg) from xpt
        for id_ in self.target_IDs:
            target = Target(id=id_)
            for mcu_num in [1, 2]:
                val_fw = getattr(self, f"firmware{mcu_num}")
                has_fw = val_fw is not None
                tgt_mcu = target[f"mcu{mcu_num}"]
                has_mcu = tgt_mcu is not None
                if not has_fw and has_mcu:
                    fw_def = Firmware(name=tgt_mcu.fw_name_default)
                    # ⤷ this will raise if default is faulty
                    if tgt_mcu.id != fw_def.mcu.id:
                        msg = (
                            f"Default-Firmware for MCU{mcu_num} of Target-ID '{target.id}' "
                            f"(={fw_def.mcu.name}) "
                            f"is incompatible (={tgt_mcu.name})"
                        )
                        raise ValueError(msg)
                if has_fw and has_mcu and val_fw.mcu.id != tgt_mcu.id:
                    msg = (
                        f"Firmware{mcu_num} for MCU of Target-ID '{target.id}' "
                        f"(={val_fw.mcu.name}) "
                        f"is incompatible (={tgt_mcu.name})"
                    )
                    raise ValueError(msg)

        c_ids = self.custom_IDs
        t_ids = self.target_IDs
        if c_ids is not None and (len(set(c_ids)) < len(set(t_ids))):
            msg = f"Provided custom IDs {c_ids} not enough to cover target range {t_ids}"
            raise ValueError(msg)
        # TODO: if custom ids present, firmware must be ELF
        if self.target_delays is not None:
            log.warning("Feature TargetDelays is reserved for future use (not implemented).")
        if self.gpio_actuation is not None:
            log.warning("Feature GpioActuation is reserved for future use (not implemented).")
        return self

    def get_custom_id(self, target_id: int) -> int | None:
        if self.custom_IDs is not None and target_id in self.target_IDs:
            return self.custom_IDs[self.target_IDs.index(target_id)]
        return None

    def get_critical_paths(self) -> set[Path]:
        """Return all paths of non-repeatable energy profiles to warn about re-usage."""
        paths: list[Path] = [
            profile.data_path
            for profile in self.energy_env.energy_profiles
            if not profile.repetitions_ok
        ]
        path_set = set(paths)
        if len(paths) != len(path_set):
            log.warning(
                f"Detected re-usage of non-repeatable EnergyProfiles "
                f"in EnergyEnv '{self.energy_env.name}' (TargetConfig-Level)"
            )
        return path_set
