"""Third prototype for an improved EEnv-Dataclass that introduces a chained builder-class.

## Pros

- makes it easier to construct complex scenarios

## Cons

- very early prototype / not finished ATM
- chained setting of firmware (unaware of actual target) is messy (firmware1, firmware2 possible)
- setting other params of TargetConfig is unsolved

"""

from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from typing import Self

from pydantic import Field
from pydantic import validate_call
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import EnergyProfile
from shepherd_core.data_models import ShpModel
from shepherd_core.data_models.content.virtual_source_config import VirtualSourceConfig
from shepherd_core.data_models.experiment.observer_features import GpioActuation
from shepherd_core.data_models.experiment.observer_features import GpioTracing
from shepherd_core.data_models.experiment.observer_features import PowerTracing
from shepherd_core.data_models.experiment.observer_features import UartLogging

from shepherd_core import log


class Firmware(ShpModel):
    name: str


class TargetConfig(ShpModel):
    # TODO: biggest change as this only reflects the config of ONE target

    target_ID: int
    custom_ID: int | None = None

    energy_profile: EnergyProfile

    """ input for the virtual source """
    virtual_source: VirtualSourceConfig | None = None
    # TODO: made this none for testing

    firmware: Firmware | None
    # TODO: made this optional for demo

    power_tracing: PowerTracing | None = None
    gpio_tracing: GpioTracing | None = None
    gpio_actuation: GpioActuation | None = None
    uart_logging: UartLogging | None = None


class Experiment(ShpModel):
    target_configs: Annotated[list[TargetConfig], Field(min_length=1, max_length=128)]


class TargetConfigBuilder:
    @validate_call
    def __init__(
        self,
        target_IDs: Sequence[int],
        firmware_default: Firmware | None = None,
        energy_profile_default: EnergyProfile | None = None,
    ) -> None:
        self.target_IDs: list[int] = list(target_IDs)
        self.firmwares: list[Firmware | None] = len(target_IDs) * [firmware_default]
        self.profiles: list[EnergyProfile | None] = len(target_IDs) * [energy_profile_default]
        # TODO: other fields missing
        # TODO: use all IDs if None is provided?
        # TODO: either provide defaults here OR in the .with_() function
        # TODO: use static 3V profile if None is provided?
        # TODO: target_ID is available, so default firmware could be derived from target

    @validate_call
    def with_firmware(self, firmware: Firmware, target_IDs: Sequence[int] | None = None) -> Self:
        if target_IDs is None:
            target_IDs = self.target_IDs
        for i in range(len(self.target_IDs)):
            if self.target_IDs[i] in target_IDs:
                self.firmwares[i] = firmware
        return self

    @validate_call
    def with_eenv(self, eenv: EnergyEnvironment, mapping: Mapping[int, int] | None = None) -> Self:
        if mapping is None:
            mapping = {id_: iter_ for (iter_, id_) in enumerate(self.target_IDs)}

        for iter_, id_ in enumerate(self.target_IDs):
            if id_ in mapping:
                self.profiles[iter_] = eenv[mapping.get(id_)]
        return self

    def build(self) -> list[TargetConfig]:
        return [
            TargetConfig(
                target_ID=self.target_IDs[i],
                firmware=self.firmwares[i],
                energy_profile=self.profiles[i],
            )
            for i in range(len(self.target_IDs))
        ]


if __name__ == "__main__":
    # Dummy firmware
    dummy_fw1 = Firmware(name="Dummy Firmware 1")
    dummy_fw2 = Firmware(name="Another Firmware")

    # Dummy eenv (this would correspond to an eenv from the server)
    dummy_profiles = [
        EnergyProfile(
            data_path=Path(f"./file_{_i}.h5"),
            data_type=EnergyDType.ivcurve,
            duration=3600,
            energy_Ws=3.1,
            valid=True,
        )
        for _i in range(10)
    ]
    dummy_eenv1 = EnergyEnvironment(
        id=9999,
        name="Dummy Experiment",
        energy_profiles=dummy_profiles,
        owner="jane",
        group="wayne",
    )
    dummy_eenv2 = EnergyEnvironment(
        id=77,
        name="Another Experiment",
        energy_profiles=dummy_profiles[:2],
        owner="jane",
        group="wayne",
    )

    log.info("Minimal Configuration:")
    cfgs = (
        TargetConfigBuilder(target_IDs=range(10, 14))
        .with_firmware(dummy_fw1)
        .with_eenv(dummy_eenv1)
        .build()
    )
    log.info(
        Experiment(target_configs=cfgs).model_dump_json(
            indent=3, exclude_unset=True, exclude_defaults=True
        )
    )
    log.info("---\n\n")

    log.info("Mixed Environments:")
    cfgs_2 = (
        TargetConfigBuilder(target_IDs=range(10, 15))
        .with_firmware(dummy_fw1)
        .with_eenv(dummy_eenv1, mapping={10: 1, 11: 2, 12: 3})
        .with_eenv(dummy_eenv2, mapping={13: 0, 14: 1})
        .build()
    )
    log.info(
        Experiment(target_configs=cfgs_2).model_dump_json(
            indent=3, exclude_unset=True, exclude_defaults=True
        )
    )
    log.info("---\n\n")

    log.info("Complex/Manual Configuration:")
    cfgs_3 = target_configs = [
        TargetConfig(target_ID=4, firmware=dummy_fw1, energy_profile=dummy_profiles[0]),
        TargetConfig(target_ID=7, firmware=dummy_fw2, energy_profile=dummy_profiles[0]),
        TargetConfig(target_ID=13, firmware=dummy_fw1, energy_profile=dummy_profiles[7]),
        TargetConfig(target_ID=22, firmware=dummy_fw1, energy_profile=dummy_profiles[3]),
    ]
    log.info(
        Experiment(target_configs=cfgs_3).model_dump_json(
            indent=3, exclude_unset=True, exclude_defaults=True
        )
    )
    log.info("---\n\n")
