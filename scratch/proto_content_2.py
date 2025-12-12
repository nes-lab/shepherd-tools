"""Second prototype for an improved EEnv-Dataclass."""

import shutil
from collections.abc import Iterable
from copy import deepcopy
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from typing import Any
from typing import overload

import yaml
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call
from shepherd_core.data_models import ShpModel
from typing_extensions import Self

from shepherd_core import log


class EnergyDType(str, Enum):
    """Data-Type-Options for energy environments."""

    ivtrace = ivsample = ivsamples = "ivsample"
    ivsurface = ivcurve = ivcurves = "ivcurve"
    isc_voc = "isc_voc"


# TODO: export of eenv


class EnergyProfile(BaseModel):
    data_path: Path

    max_harvestable_energy: PositiveFloat | None = None

    data_type: EnergyDType

    metadata: dict | None = None

    model_config = ConfigDict(
        use_enum_values=True,
    )

    @model_validator(mode="before")
    @classmethod
    def cast_path(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "data_path" in values and isinstance(values["data_path"], Iterable):
            values["data_path"] = values["data_path"].absolute()
        return values


class EnergyEnvironment2(ShpModel):
    profiles: list[EnergyProfile]
    # ⤷  list of individual profiles that make up the environment

    duration: PositiveFloat
    # ⤷  in s; duration of the recorded environment (of all profiles)
    # TODO: move duration to profile and add @property here that iterates/min()

    # TODO: add datalib_version ??
    metadata: str | None = None
    # ⤷  information about the environment as a dict

    def __len__(self) -> int:
        return len(self.profiles)

    @validate_call(validate_return=False)
    def __add__(self, other: ShpModel) -> Self:
        if not isinstance(other, EnergyEnvironment2):
            raise TypeError("rvalue must be same type")
        return self.model_copy(
            deep=True, update={"profiles": deepcopy(self.profiles + other.profiles)}
        )
        # TODO: what about other fields like metadata -> join dict? only keep dict of first?

    @overload
    def __getitem__(self, value: int) -> EnergyProfile: ...
    @overload
    def __getitem__(self, value: slice) -> "EnergyEnvironment2": ...
    def __getitem__(self, value):
        if isinstance(value, int):
            return deepcopy(self.profiles[value])
        if isinstance(value, slice):
            return self.model_copy(deep=True, update={"profiles": deepcopy(self.profiles[value])})
        raise IndexError("please use int or slice to choose")

    def export(self, output_path: Path) -> None:
        """Copy local data and add information-file."""
        if output_path.exists():
            log.warning(f"Warning: path {output_path} already exists")
        output_path.mkdir(exist_ok=True)  # TODO: should be disabled in finale implementation
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


class TargetConfig2(ShpModel):
    """Prototype."""

    target_IDs: Annotated[list[int], Field(min_length=1, max_length=128)]
    eenv: EnergyEnvironment2

    @model_validator(mode="after")
    def check_eenv_count(self) -> Self:
        n_eenv = len(self.eenv)
        n_target = len(self.target_IDs)
        if n_eenv == n_target:
            return self

        if n_eenv > n_target:
            msg = (
                f"Creating config for {n_target} sheep with {n_eenv} energy profiles. "
                f"Remainder of the env will be discarded."
            )
            log.warning(msg)
            return self

        if n_eenv == 1:  # TODO: should be explicitly allowed
            msg = (
                f"Creating config for {n_target} sheep with {n_eenv} energy profiles. "
                f"Environment will be duplicated across the targets."
            )
            log.warning(msg)
            return self

        msg = (
            f"Creating config for {n_target} sheep with {n_eenv} energy profiles. "
            f"Can not infer a mapping of environment -> targets. "
            f"Please use a larger environment."
        )
        raise ValueError(msg)


if __name__ == "__main__":
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path1 = Path(tmp) / "shp1.h5"
        path2 = Path(tmp) / "shp3.h5"
        path1.touch()
        path2.touch()
        profile1 = EnergyProfile(
            data_path=path1, data_type=EnergyDType.ivtrace, max_harvestable_energy=1
        )
        profile2 = EnergyProfile(
            data_path=path2, data_type=EnergyDType.ivtrace, max_harvestable_energy=1
        )
        eenv1 = EnergyEnvironment2(profiles=[profile1, profile2], duration=1)
        log.info(f"EEnv1\t{eenv1.model_dump(exclude_unset=True, exclude_defaults=True)}")

        eenv2a = eenv1[1:]
        eenv2b = eenv1[:1]
        eenv2 = eenv2a + eenv2b
        log.info(f"EEnv2a\t{eenv2a.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2b\t{eenv2b.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2\t{eenv2.model_dump(exclude_unset=True, exclude_defaults=True)}")

        eenv3 = eenv1 + eenv1
        log.info(f"EEnv3\t{eenv1.model_dump(exclude_unset=True, exclude_defaults=True)}")

        eenv2.export(Path(tmp) / "export")
        log.info("Config 1 - 2:2")
        TargetConfig2(target_IDs=range(2), eenv=eenv1)
        log.info("Config 2 - 1:2")
        TargetConfig2(target_IDs=range(1), eenv=eenv2)
        log.info("Config 3 - 3:1")
        TargetConfig2(target_IDs=range(3), eenv=eenv1[:1])
        log.info("Config 4 - 4:4")
        TargetConfig2(target_IDs=range(4), eenv=eenv3)
        log.info("Config 5 - 4:2 -> raises")
        TargetConfig2(target_IDs=range(4), eenv=eenv1)
