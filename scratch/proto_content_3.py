"""Third prototype for an improved EEnv-Dataclass."""

import shutil
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Self

import yaml
from pydantic import Field
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call
from shepherd_core.data_models import ShpModel
from shepherd_core.data_models.content.virtual_source_config import VirtualSourceConfig
from shepherd_core.data_models.experiment.observer_features import GpioActuation
from shepherd_core.data_models.experiment.observer_features import GpioTracing
from shepherd_core.data_models.experiment.observer_features import PowerTracing
from shepherd_core.data_models.experiment.observer_features import UartLogging

from shepherd_core import log


class Firmware(ShpModel):
    name: str


class EnergyEnvironment(ShpModel):
    name: str
    # TODO: this would be part of ContentModel

    data_paths: list[Path]
    # ⤷  list of data files corresponding to the nodes

    duration: PositiveFloat
    # ⤷  in s; duration of the recorded environment (of all profiles)

    metadata: dict | None = None
    # ⤷  information about the environment as a dict

    def export(self, output_path: Path) -> None:
        """Copy local data and add information-file."""
        output_path.mkdir(exist_ok=False)
        profile_paths: list[Path] = []

        # Copy data files
        for i_, profile in enumerate(self.profiles):
            # Number the sheep to avoid collisions. Preserve extensions
            file_name = f"node{i_:03d}{profile.data_path.suffix}"
            shutil.copy(profile.data_path, output_path / file_name)
            profile_paths.append(output_path / file_name)

        # Create information file
        content = self.model_dump(exclude_unset=True, exclude_defaults=True)
        for i_, path in enumerate(profile_paths):
            content["profiles"][i_]["data_path"] = path
        with (output_path / "eenv.yaml").open("w") as file:
            yaml.safe_dump(content, file, default_flow_style=False, sort_keys=False)

    @model_validator(mode="before")
    @classmethod
    def cast_path(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "data_paths" in values and isinstance(values["data_paths"], Iterable):
            values["data_paths"] = [path.absolute() for path in values["data_paths"]]
        return values


class TargetConfig(ShpModel):
    target_ID: int
    custom_ID: int | None = None

    energy_profile: tuple[str, int]

    """ input for the virtual source """
    virtual_source: VirtualSourceConfig | None = None
    # TODO: made this none for testing

    target_delays: (
        Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1, max_length=128)] | None
    ) = None
    """ ⤷ individual starting times

    - allows to use the same environment
    - not implemented ATM
    """

    # TODO: made this optional for demo
    firmware1: Firmware | None
    """ ⤷ omitted FW gets set to neutral deep-sleep"""
    firmware2: Firmware | None = None
    """ ⤷ omitted FW gets set to neutral deep-sleep"""

    power_tracing: PowerTracing | None = None
    gpio_tracing: GpioTracing | None = None
    gpio_actuation: GpioActuation | None = None
    uart_logging: UartLogging | None = None


class Experiment(ShpModel):
    """Config for experiments on the testbed emulating energy environments for target nodes."""

    target_configs: Annotated[list[TargetConfig], Field(min_length=1, max_length=128)]


class TargetConfigBuilder:
    @validate_call
    def __init__(self, target_IDs: Sequence[int]) -> None:
        self.target_IDs = target_IDs
        self.firmwares: list[Firmware | None] = len(target_IDs) * [None]
        self.eenvs: list[tuple[str, int] | None] = len(target_IDs) * [None]
        # TODO: shouldn't eenv also hold single EenvProfiles?

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
                self.eenvs[iter_] = (eenv.name, mapping[id_])

        return self

    def build(self) -> list[TargetConfig]:
        return [
            TargetConfig(
                target_ID=self.target_IDs[i],
                firmware1=self.firmwares[i],
                energy_profile=self.eenvs[i],
            )
            for i in range(len(self.target_IDs))
        ]


if __name__ == "__main__":
    # Dummy firmware
    dummy_fw = Firmware(name="Dummy Firmware")
    dummy_fw_2 = Firmware(name="Another Firmware")

    # Dummy eenv (this would correspond to an eenv from the server)
    path1 = Path("./shp1.h5")
    path2 = Path("./shp2.h5")
    path3 = Path("./shp3.h5")
    path4 = Path("./shp4.h5")
    dummy_eenv = EnergyEnvironment(
        name="Dummy Experiment", data_paths=[path1, path2], duration=3600, metadata={}
    )
    # Imagine this is a different energy environment
    dummy_eenv_2 = EnergyEnvironment(
        name="Another Experiment", data_paths=[path1, path2], duration=3600, metadata={}
    )

    log.info("Minimal Configuration:")
    cfgs = (
        TargetConfigBuilder(target_IDs=range(10, 14))
        .with_firmware(dummy_fw)
        .with_eenv(dummy_eenv)
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
        .with_firmware(dummy_fw)
        .with_eenv(dummy_eenv, mapping={10: 1, 11: 2, 12: 3})
        .with_eenv(dummy_eenv_2, mapping={13: 0, 14: 1})
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
        TargetConfig(target_ID=4, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 0)),
        TargetConfig(target_ID=7, firmware1=dummy_fw_2, energy_profile=(dummy_eenv.name, 0)),
        TargetConfig(target_ID=13, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 7)),
        TargetConfig(target_ID=22, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 3)),
    ]
    log.info(
        Experiment(target_configs=cfgs_3).model_dump_json(
            indent=3, exclude_unset=True, exclude_defaults=True
        )
    )
    log.info("---\n\n")
