"""Data-model for recorded Energy-Environments (EEnvs).

Scalar environment-recordings are called EnergyProfiles (only temporal dimension).
EnergyEnvironments are metadata representations of spatio-temporal energy-recordings.

Features:
- environments hold >= 1 profile / recording
- allows mapping profiles to individual targets (in target config)
- emit warning if single EEnv is used more than once to avoid unwanted correlation effects
  - exception to that rule if EEnv allows for it (repetition_ok)
  - checked on local TargetConfig-level and more global on experiment-level
- avoid funky behavior & hidden mechanics
- environments can be composed (add single profiles, list of profiles or a 2nd environment)
- offer structured metadata (dict) for information about the environment
- access elements similar to list[]-syntax for single items and slices

Profiles embed generalized metadata:
- duration of the recording,
- maximum harvestable energy,
- flag to signal a valid recording file,
- flag to signal that repetitions are okay -> typically used by
  static / artificial traces that don't cause unwanted correlation effects

Typical additional metadata keys for Energy Environments:
  - recording-tool/generation-script,
  - [maximum harvestable energy] -> already hardcoded
  - location (address/GPS),
  - site-description (building/forest),
  - weather,
  - node specific data, like
    - transducer used
    - location within experiment

TODO: add TargetConfig-Builder that makes it easier to construct complex scenarios
      see proto_target_config_builder.py
TODO: find a proper solution for slicing repetitions (consider slice-length)
      or get rid of funky behavior (warning is emitted ATM)
"""

import shutil
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import final
from typing import overload

import yaml
from pydantic import Field
from pydantic import NonNegativeFloat
from pydantic import PositiveFloat
from pydantic import model_validator
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.content import id_default
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.timezone import local_now
from shepherd_core.logger import log
from shepherd_core.reader import Reader
from shepherd_core.testbed_client import tb_client

from .enum_datatypes import EnergyDType


@final
class EnergyProfile(ShpModel):
    """Metadata representation of scalar energy-recording."""

    data_path: Path
    data_type: EnergyDType
    data_2_copy: bool = True
    """ ⤷ signals that file has to be copied to testbed"""

    duration: PositiveFloat
    energy_Ws: NonNegativeFloat
    """ ⤷ maximum usable energy """
    valid: bool = False
    """ ⤷ profile is marked invalid by default to:
            - motivate using .from_file(), or
            - easier find manual validity-overrides
    """
    repetitions_ok: bool = False
    """⤷ emit no warning if single profile-path is used more than once.
    this protects against unwanted correlation effects.
    """

    def export(self, output_path: Path) -> Self:
        """Copy this EnergyProfile to a new destination."""
        if not self.data_path.exists():
            raise FileNotFoundError("EnergyProfile is not locally available.")
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
        try:
            with Reader(self.data_path) as reader:
                if self.duration != reader.runtime_s:
                    log.error(
                        f"EnergyProfile duration does not match runtime of file ({self.data_path})."
                    )
                    return False
                if self.valid != reader.is_valid():
                    log.error(
                        f"EnergyProfile validity-state does not match file ({self.data_path})."
                    )
                    return False
                if self.energy_Ws != reader.energy():
                    log.error(f"EnergyProfile max energy does not match file ({self.data_path}).")
                    return False
        except TypeError:
            log.error(f"EnergyProfile - hdf5-file could not be read ({self.data_path})")
            return False
        return True

    def exists(self) -> bool:
        """Check if embedded file exists."""
        return self.data_path.exists()

    @classmethod
    def derive_from_file(
        cls,
        hdf: Path,
        data_type: EnergyDType | None = None,
        *,
        repetition_ok: bool = False,
    ) -> Self:
        """Use recording to fill in most fields."""
        with Reader(hdf, verbose=False) as reader:
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

    energy_profiles: Annotated[list[EnergyProfile], Field(min_length=1)]
    """ ⤷  list of individual profiles that make up the environment"""

    metadata: Mapping[str, str | int | float] = {}
    """ ⤷ additional descriptive information

    Example for solar: (main) light source, weather conditions, indoor
    General: transducer / harvester used, date, time, experiment setup, location, route
    """

    modifications: Sequence[str] = []
    """Changes recorded by manipulation-Ops (i.e. addition, slicing)."""

    # TODO: scale up/down voltage/current
    # TODO: mean power as energy/duration

    PROFILES_MAX: int = Field(default=128, exclude=True)
    """ ⤷ arbitrary maximum, internal state which controls behavior for repetitions_ok-cases

    - single item list access is possible as modulo
    - sliced list access repeats profile-list up to max length
        ee[10:] gets (max - 10) items
    """

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Add missing entries of class by querying database."""
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return tb_client.fill_in_user_data(values)

    def __len__(self) -> int:
        if self.repetitions_ok:
            return self.PROFILES_MAX
        return len(self.energy_profiles)

    @property
    def duration(self) -> PositiveFloat:
        """Duration of the recorded environment (minimum of all profiles) in seconds."""
        return min(profile.duration for profile in self.energy_profiles)

    @property
    def repetitions_ok(self) -> bool:
        """Emit no warning if single profile-path is used more than once."""
        return all(profile.repetitions_ok for profile in self.energy_profiles)

    @property
    def valid(self) -> bool:
        return all(profile.valid for profile in self.energy_profiles)

    def enforce_validity(self) -> None:
        """Offer soft validation that can be used by upper classes."""
        msg = f"All EnergyProfiles in EnergyEnvironment {self.name} must be marked valid."
        msg += " False for:"
        for profile in self.energy_profiles:
            if not profile.valid:
                msg += f"\n\t- {profile.data_path}"
        if not self.valid:
            raise ValueError(msg + "\n")

    @validate_call(validate_return=False)
    def __add__(self, rvalue: ShpModel | list[ShpModel]) -> Self:
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
                    f"EEnv '{self.name}' - added EnergyProfile {rvalue.data_path.stem}, "
                    f"ID [{self.id}->{id_new}]",
                ]
            )
            data["energy_profiles"] = deepcopy([*self.energy_profiles, rvalue])
            return self.model_copy(deep=True, update=data)
        if isinstance(rvalue, list):
            if len(rvalue) == 0:
                return self.model_copy(deep=True)
            if isinstance(rvalue[0], EnergyProfile):
                data["modifications"] = deepcopy(
                    [
                        *self.modifications,
                        f"EEnv '{self.name}' - added list of {len(rvalue)} EnergyProfiles, "
                        f"ID[{self.id}->{id_new}]",
                    ]
                )
                data["energy_profiles"] = deepcopy(self.energy_profiles + rvalue)
                return self.model_copy(deep=True, update=data)
            raise ValueError("Addition could not be performed, as types did not match.")
        if isinstance(rvalue, EnergyEnvironment):
            data["modifications"] = deepcopy(
                [
                    *self.modifications,
                    *rvalue.modifications,
                    f"EEnv '{self.name}' - added EEnv {rvalue.name} with {len(rvalue)} entries, "
                    f"ID[{self.id}->{id_new}]",
                ]
            )
            data["metadata"] = deepcopy({**rvalue.metadata, **self.metadata})
            # ⤷ values of right side are kept in case of key-collision
            data["energy_profiles"] = deepcopy(self.energy_profiles + rvalue.energy_profiles)
            return self.model_copy(deep=True, update=data)
        raise TypeError(
            "Right value of addition must be of type: "
            "EnergyProfile, list[EnergyProfile], EnergyEnvironment."
        )

    @overload
    def __getitem__(self, value: int) -> EnergyProfile: ...
    @overload
    def __getitem__(self, value: slice) -> Self: ...
    def __getitem__(self, value):
        """Select elements from this EEnv similar to list-Ops (slicing, int)."""
        if isinstance(value, int):
            if self.repetitions_ok:
                value = value % len(self.energy_profiles)
            return deepcopy(self.energy_profiles[value])
        if isinstance(value, slice):
            if self.repetitions_ok:
                # bring values into range (out of bounds like -1, 300, ..)
                log.warning("EEnv-Slice-Access with .repetition_ok==True is beta (funky behavior)")
                val_start = value.start % self.PROFILES_MAX if value.start else value.start
                val_stop: int = self.PROFILES_MAX
                if value.stop:
                    if value.stop < 0:
                        val_stop = value.stop % self.PROFILES_MAX
                    else:
                        val_stop = min(value.stop, self.PROFILES_MAX)

                if val_start and val_start > val_stop:
                    val_start = val_stop
            else:
                val_start = value.start
                val_stop = value.stop

            if self.repetitions_ok and val_stop > len(self.energy_profiles):
                # scale profile-list up
                scale = (val_stop // len(self.energy_profiles)) + 1
                profiles = scale * self.energy_profiles
            else:
                profiles = self.energy_profiles
            id_new = id_default()
            slice_new = slice(val_start, val_stop, value.step)
            data: dict[str, Any] = {
                "id": id_new,
                "created": local_now(),
                "updated_last": local_now(),
                "modifications": deepcopy(
                    [
                        *self.modifications,
                        f"EEnv '{self.name}' was sliced with {slice_new}, ID[{self.id}->{id_new}]",
                    ]
                ),
                "energy_profiles": deepcopy(profiles[slice_new]),
            }
            return self.model_copy(deep=True, update=data)
        raise IndexError("Use int or slice when selecting from EEnv")

    def export(self, output_path: Path) -> None:
        """Copy local data to new directory and add meta-data-file."""
        if output_path.exists():
            # TODO: elegant but unpractical, must be: empty dir or non-existing dir
            msg = f"Warning: path {output_path} already exists"
            raise FileExistsError(msg)
        output_path.mkdir(parents=True)

        # Copy data files & update meta-data
        content = self.model_dump(exclude_unset=True, exclude_defaults=True)
        for i_, profile in enumerate(self.energy_profiles):
            # Numbered to avoid collisions. Preserve extensions
            file_name = f"node{i_:03d}{profile.data_path.suffix}"
            profile_new = profile.export(output_path / file_name)
            content["energy_profiles"][i_] = profile_new.model_dump(
                exclude_unset=True, exclude_defaults=True
            )

        # Create metadata file
        with (output_path / "eenv.yaml").open("w") as file:
            yaml.safe_dump(content, file, default_flow_style=False, sort_keys=False)

    def exists(self) -> bool:
        """Check if embedded files exists."""
        return all(profile.exists() for profile in self.energy_profiles)

    def check(self) -> bool:
        """Check validity of embedded Energy-Profile."""
        return all(profile.check() for profile in self.energy_profiles)
