"""Data-model for recorded eEnvs."""

import shutil
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any
from typing import Self
from typing import final
from typing import overload

import yaml
from pydantic import NonNegativeFloat
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call

from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.content import id_default
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.timezone import local_now
from .enum_datatypes import EnergyDType
from shepherd_core.logger import log
from shepherd_core.reader import Reader
from shepherd_core.testbed_client import tb_client


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
        """Copy this EnergyProfile to a new destination."""
        if not self.data_path.exists():
            raise TypeError("EnergyProfile is not locally available.")
        if output_path.exists():
            if output_path.is_dir():
                file_path = output_path / self.data_path.name
            else:
                raise FileExistsError("Provided export-path exists, but is not a directory")
        else:
            output_path.parent.mkdir(exist_ok=True, parents=True)
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
                log.error(
                    f"EnergyProfile duration does not match runtime of file ({self.data_path})."
                )
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
                raise ValueError(
                    "EnergyDType could not be determined from file, please provide it."
                )
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

    # General Metadata & Ownership -> see ContentModel

    profiles: list[EnergyProfile]
    """ ⤷  list of individual profiles that make up the environment"""

    metadata: Mapping[str, str] = {}
    """ ⤷ additional descriptive information

    Example for solar: (main) light source, weather conditions, indoor
    General: transducer / harvester used, date, time, experiment setup, location, route
    """

    modifications: Sequence[str] = []
    """Changes recorded by manipulation-Ops (i.e. addition, slicing)."""

    # TODO: scale up/down voltage/current
    # TODO: mean power as energy/duration

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Add missing entries of class by querying database."""
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return tb_client.fill_in_user_data(values)

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

    @property
    def valid(self) -> bool:
        return all(profile.valid for profile in self.profiles)

    @validate_call(validate_return=False)
    def __add__(self, rvalue: ShpModel) -> Self:
        """Extend this EnergyEnvironment.

        Possible concatenations:
        - a single EProfile,
        - a list of EnergyProfiles,
        - a second EnergyEnvironment
        """
        id_new = id_default()
        data: dict[str, Any] = {
            "id": id_new,
            "created": local_now(),
            "updated_last": local_now(),
        }
        if isinstance(rvalue, EnergyProfile):
            data["modifications"] = deepcopy(
                [
                    *self.modifications,
                    f"{self.name} - added EnergyProfile {rvalue.data_path.stem}, "
                    f"ID [{self.id}->{id_new}]",
                ]
            )
            data["profiles"] = deepcopy([*self.profiles, rvalue])
            return self.model_copy(deep=True, update=data)
        if isinstance(rvalue, list):
            if len(rvalue) == 0:
                return self.model_copy(deep=True)
            if isinstance(rvalue[0], EnergyProfile):
                data["modifications"] = deepcopy(
                    [
                        *self.modifications,
                        f"{self.name} - added list of {len(rvalue)} EnergyProfiles, "
                        f"ID[{self.id}->{id_new}]",
                    ]
                )
                data["profiles"] = deepcopy(self.profiles + rvalue)
                return self.model_copy(deep=True, update=data)
            raise ValueError("Addition could not be performed, as types did not match.")
        if isinstance(rvalue, EnergyEnvironment):
            data["modifications"] = deepcopy(
                [
                    *self.modifications,
                    *rvalue.modifications,
                    f"{self.name} - added EEnv {rvalue.name} with {len(rvalue)} entries, "
                    f"ID[{self.id}->{id_new}]",
                ]
            )
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
        """Select elements from this EEnv similar to list-Ops (slicing, int)."""
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
            id_new = id_default()
            data: dict[str, Any] = {
                "id": id_new,
                "created": local_now(),
                "updated_last": local_now(),
                "modifications": deepcopy(
                    [
                        *self.modifications,
                        f"{self.name} was sliced with {value}, ID[{self.id}->{id_new}]",
                    ]
                ),
                "profiles": deepcopy(profiles[value]),
            }
            return self.model_copy(deep=True, update=data)
        raise IndexError("Use int or slice when selecting from EEnv")

    def export(self, output_path: Path) -> None:
        """Copy local data to new directory and add meta-data-file."""
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
        """Check validity of embedded Energy-Profile."""
        return all(profile.check() for profile in self.profiles)
