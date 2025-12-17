"""Fourth prototype for an improved EEnv-Dataclass.

Mix of Prototype 1 & 2 with additional refinements.
"""

import shutil
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Mapping
from typing import Any
from typing import Self
from typing import final
from typing import overload

import yaml
from pydantic import Field
from pydantic import NonNegativeFloat
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call
from shepherd_core.data_models import ContentModel
from shepherd_core.data_models import ShpModel
from shepherd_core.data_models.base.content import id_default
from shepherd_core.data_models.content import EnergyDType
from shepherd_core.testbed_client import tb_client
from typing_extensions import deprecated

from shepherd_core import Reader
from shepherd_core import local_now
from shepherd_core import log


@final
class EnergyProfile(ShpModel):
    """Metadata representation of scalar energy-recording."""

    data_path: Path
    data_type: EnergyDType
    data_2_copy: bool = True
    """ ⤷ signals that file has to be copied to testbed"""

    duration: PositiveFloat
    energy_Ws: NonNegativeFloat
    """ ⤷ max usable energy """
    valid: bool = False
    repetitions_ok: bool = False
    """⤷ emit no warning if single profile-path is used more than once.
    this protects against unwanted correlation effects.
    """

    def export(self, output_path: Path) -> Self:
        if not self.data_path.exists():
            raise TypeError("EnergyProfile is not locally available.")
        log.debug(f"{self.data_path.stem}-EProfile export was called -> {output_path}")
        if output_path.exists():
            if output_path.is_dir():
                file_path = output_path / self.data_path.name
            else:
                raise FileExistsError("Provided export-path exists, but is not a directory")
        else:
            # output_path.mkdir(exist_ok=False)
            file_path = output_path
        # TODO: offer both, move and copy?
        shutil.copy(self.data_path, file_path)
        return self.model_copy(deep=True, update={"data_path": file_path})

    def check(self) -> bool:
        """Check validity of Energy-Profile.

        Path must exist, be a file, be shepherd-hdf5-format.
        """
        if not self.data_path.exists():
            log.error(f"EnergyProfile does not exist in '{self.data_path}'.")
            return False
        if not self.data_path.is_file():
            log.error(f"EnergyProfile is not a file ({self.data_path}).")
            return False
        with Reader(self.data_path) as reader:
            if self.duration != reader.runtime_s:
                log.error(f"EnergyProfile duration does not match runtime of file ({self.data_path}).")
                return False
            if self.valid != reader.is_valid():
                log.error(f"EnergyProfile validity-state does not match file ({self.data_path}).")
                return False
            if self.energy_Ws != reader.energy():
                log.error(f"EnergyProfile max energy does not match file ({self.data_path}).")
                return False
        return True

    @classmethod
    def derive_from_file(
        cls,
        hdf: Path,
        data_type: EnergyDType | None = None,
        *,
        repetition_ok: bool = False,
    ) -> Self:
        """Use recording to fill in most fields."""
        with Reader(hdf) as reader:
            dtype = data_type or reader.get_datatype()
            if dtype is None:
                raise ValueError("EnergyDType could not be determined from file, please provide it.")
            return cls(
                data_path=hdf,
                data_type=dtype,
                data_2_copy=True,
                duration=reader.runtime_s,
                energy_Ws=reader.energy(),
                valid=reader.is_valid(),
                repetitions_ok=repetition_ok,
            )


@final
class EnergyEnvironment(ContentModel):
    """Metadata representation of spatio-temporal energy-recording."""

    profiles: list[EnergyProfile]
    """ ⤷  list of individual profiles that make up the environment"""

    metadata: Mapping[str, str] = {}
    """ ⤷ additional descriptive information

    Example for solar: (main) light source, weather conditions, indoor, location
    """

    modifications: Sequence[str] = []

    def __len__(self) -> int:
        return len(self.profiles)

    @property
    def duration(self) -> PositiveFloat:
        """Duration of the recorded environment (minimum of all profiles) in seconds."""
        return min(profile.duration for profile in self.profiles)

    @property
    def repetitions_ok(self) -> bool:
        """Emit no warning if single profile-path is used more than once."""
        return all(profile.repetitions_ok for profile in self.profiles)

    @validate_call(validate_return=False)
    def __add__(self, rvalue: ShpModel) -> Self:
        data: dict[str, Any] = {
            "id": id_default(),
            "created": local_now(),
            "updated_last": local_now(),
        }
        if isinstance(rvalue, EnergyProfile):
            data["modifications"] = deepcopy([*self.modifications, f"{self.name} - added EnergyProfile {rvalue.data_path.stem}"])
            data["profiles"] = deepcopy([*self.profiles, rvalue])
            return self.model_copy(deep=True, update=data)
        if isinstance(rvalue, list):
            if len(rvalue) == 0:
                return self.model_copy(deep=True)
            if isinstance(rvalue[0], EnergyProfile):
                data["modifications"] = deepcopy([*self.modifications, f"{self.name} - added list of {len(rvalue)} EnergyProfiles"])
                data["profiles"] = deepcopy(self.profiles + rvalue)
                return self.model_copy(deep=True, update=data)
            raise ValueError("Addition could not be performed, as types did not match.")
        if isinstance(rvalue, EnergyEnvironment):
            data["modifications"] = deepcopy([*self.modifications, *rvalue.modifications, f"{self.name} - added EnergyEnvironment {rvalue.name} with {len(rvalue)} entries"])
            data["metadata"] = deepcopy({**rvalue.metadata, **self.metadata})
            # ⤷ right side of dict-merge is kept in case of key-collision
            data["profiles"] = deepcopy(self.profiles + rvalue.profiles)
            return self.model_copy(deep=True, update=data)
        raise TypeError("rvalue must be same type")

    @overload
    def __getitem__(self, value: int) -> EnergyProfile: ...
    @overload
    def __getitem__(self, value: slice) -> Self: ...
    def __getitem__(self, value):
        if isinstance(value, int):
            return deepcopy(self.profiles[value])
        if isinstance(value, slice):
            if value.stop and value.stop > 1000:
                msg = f"Value {value} is far out of range."
                raise ValueError(msg)
            if self.repetitions_ok and value.stop < len(self):
                # scale profile-list up
                scale = (value.stop // len(self)) + 1
                profiles = scale * self.profiles
            else:
                profiles = self.profiles
            data: dict[str, Any] = {
                "id": id_default(),
                "created": local_now(),
                "updated_last": local_now(),
                "modifications": deepcopy([*self.modifications, f"{self.name} was sliced with {value}"]),
                "profiles": deepcopy(profiles[value]),
            }
            return self.model_copy(deep=True, update=data)
        raise IndexError("Use int or slice when selecting from EEnv")

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return tb_client.fill_in_user_data(values)

    def export(self, output_path: Path) -> None:
        """Copy local data and add meta-data-file."""
        if output_path.exists():
            msg = f"Warning: path {output_path} already exists"
            raise FileExistsError(msg)
        output_path.mkdir(parents=True)

        # Copy data files & update meta-data
        content = self.model_dump(exclude_unset=True, exclude_defaults=True)
        for i_, profile in enumerate(self.profiles):
            # Numbered to avoid collisions. Preserve extensions
            file_name = f"node{i_:03d}{profile.data_path.suffix}"
            profile_new = profile.export(output_path / file_name)
            content["profiles"][i_] = profile_new.model_dump(
                exclude_unset=True, exclude_defaults=True
            )

        # Create metadata file
        with (output_path / "eenv.yaml").open("w") as file:
            yaml.safe_dump(content, file, default_flow_style=False, sort_keys=False)

    def check(self) -> bool:
        return all(profile.check() for profile in self.profiles)


@final
class TargetConfig(ShpModel):
    """Configuration related to Target Nodes (DuT)."""

    target_IDs: Annotated[Sequence[int], Field(min_length=1, max_length=128)]
    energy_env: EnergyEnvironment
    """ input for the virtual source """

    @model_validator(mode="after")
    def check_eenv_count(self) -> Self:
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


# TODO:
#   - add & change metadata
#   - add unittests


if __name__ == "__main__":
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path1 = Path(tmp) / "shp1.h5"
        path2 = Path(tmp) / "shp3.h5"
        path1.touch()
        path2.touch()
        profile1 = EnergyProfile(
            data_path=path1,
            data_type=EnergyDType.ivtrace,
            energy_Ws=1.0,
            duration=23,
        )
        profile2 = EnergyProfile(
            data_path=path2,
            data_type=EnergyDType.ivtrace,
            energy_Ws=3.0,
            duration=20,
        )
        eenv1 = EnergyEnvironment(name="t1", profiles=[profile1, profile2])
        print(f"Duration: {eenv1.duration}")
        print(f"Repetitions: {eenv1.repetitions_ok}")

        eenv2a = eenv1[1:]
        eenv2b = eenv1[:1]
        eenv2 = eenv2a + eenv2b
        log.info(f"EEnv2a\t{eenv2a.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2b\t{eenv2b.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2\t{eenv2.model_dump(exclude_unset=True, exclude_defaults=True)}")

        eenv3 = eenv1 + eenv1
        log.info(f"EEnv3\t{eenv1.model_dump(exclude_unset=True, exclude_defaults=True)}")
        eenv3.to_file(Path(__file__).parent / "eenv.yaml", minimal=True)

        profileR = EnergyProfile(
            data_path=Path(tmp) / "shp5.h5",
            data_type=EnergyDType.ivtrace,
            energy_Ws=3.0,
            duration=20,
            repetitions_ok=True,
        )
        eenvR = EnergyEnvironment(name="t1", profiles=[profileR])
        eenvR.to_file(Path(__file__).parent / "eenvR.yaml", minimal=True)

        log.info("Config 1 - 2:2")
        TargetConfig(target_IDs=range(2), energy_env=eenv1)
        log.info("Config 2 - 1:2")
        TargetConfig(target_IDs=range(1), energy_env=eenv2)
        log.info("Config 3 - 3:1R")
        tc3 = TargetConfig(target_IDs=range(3), energy_env=eenvR)
        log.info("Config 4 - 4:4")
        TargetConfig(target_IDs=range(4), energy_env=eenv3)
        log.info("Config 5 - 4:2 -> raises")
        TargetConfig(target_IDs=range(4), energy_env=eenv1)
