"""Prototype for an improved EEnv-Dataclass.

Goals:
- add structured metadata (dict)
- relative paths - with real inputs (full Path() to rel)
   - files get created locally (then copied) or right away in content-directory on server
- allow list of paths, or even dict, but still allow slice[:] operation
- avoid funky behavior & hidden mechanics
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from pathlib import Path
from pathlib import PurePosixPath
from typing import Annotated
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from shepherd_core.data_models import ShpModel
from shepherd_core.logger import log

# TODO: should dtype, duration, energy_Ws be kept with the path?
#       So we would have to create a scalar energy profile


class EEnv2(BaseModel):
    """Prototype."""

    name: str
    metadata: dict[str, str] = {}
    """⤷ structured info about content"""

    data_paths: Annotated[list[PurePosixPath], Field(min_length=1, max_length=128)]
    """⤷ relative paths to content."""
    repetitions_ok: bool = False
    """⤷ emit no warning if single eenv-path is used more than once.
    unwanted correlation effects might appear.
    """
    is_atomic: bool = False
    """⤷ atoms can't be sliced further - will be True if sliced once."""

    def __getitem__(self, value: int | slice) -> EEnv2 | list[EEnv2]:
        content = self.model_dump(exclude_defaults=True)
        content["is_atomic"] = True
        if self.is_atomic:
            raise IndexError("was already indexed / sliced")
        if isinstance(value, slice):
            nums = range(len(self.data_paths))[value]
            elements = []
            for num in nums:
                element = copy.deepcopy(content)
                element["name"] = element["name"] + "_" + str(num)
                element["data_paths"] = [element["data_paths"][num]]
                elements.append(EEnv2(**element))
            return elements
        if isinstance(value, int):
            content["name"] = content["name"] + "_" + str(value)
            content["data_paths"] = [content["data_paths"][value]]
            return EEnv2(**content)
        raise IndexError("please use int or slice to choose")

    def __len__(self) -> int:
        return len(self.data_paths)

    @model_validator(mode="before")
    @classmethod
    def cast_paths(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "data_paths" in values and isinstance(values["data_paths"], Iterable):
            # convert every path into PurePosix
            values["data_paths"] = [PurePosixPath(p_) for p_ in values["data_paths"]]
            # try deriving relative paths from absolute ones
            paths_rel = []
            path_cwd = Path().cwd()
            for path in values["data_paths"]:
                if path.is_absolute():
                    if path.is_relative_to(path_cwd):
                        paths_rel.append(path.relative_to(path_cwd))
                        continue
                    msg = f"Use relative paths - can't derive from absolute '{path}'"
                    log.warning(msg)
                paths_rel.append(path)
            values["data_paths"] = paths_rel
        return values


class TargetConfig2(ShpModel):
    """Prototype."""

    target_IDs: Annotated[list[int], Field(min_length=1, max_length=128)]
    eenvs: list[EEnv2]

    @model_validator(mode="before")
    @classmethod
    def cast_eenvs(cls, values: dict[str, Any]) -> dict[str, Any]:
        # encapsulate single eenv in list
        if "eenvs" in values and isinstance(values["eenvs"], EEnv2):
            values["eenvs"] = values["eenvs"][:]
        # atomize all eenvs
        if "eenvs" in values and isinstance(values["eenvs"], Iterable):
            eenvs = []
            for eenv in values["eenvs"]:
                if eenv.is_atomic:
                    eenvs.append(eenv)
                else:
                    eenvs += eenv[:]
            values["eenvs"] = eenvs

        return values


if __name__ == "__main__":
    eenv1 = EEnv2(
        name="complex-env",
        data_paths=[Path(".nagut"), Path("/pagut"), PurePosixPath("spaghetti")],
        repetitions_ok=False,
    )

    # options to choose elements from Eenv2
    slice1 = eenv1[2]  # eenv[5] errors with "out of range"
    slice3 = eenv1[1:]
    slice4 = eenv1[:]  # all

    target_config1 = TargetConfig2(
        target_IDs=range(5),
        eenvs=eenv1,  # will be transformed to list
    )

    eenv2 = EEnv2(
        name="static-env",
        data_paths=40 * [Path(".samesame")],
        repetitions_ok=True,
    )
    target_config2 = TargetConfig2(
        target_IDs=range(5),
        eenvs=[eenv1, eenv2],
        # TODO: find pretty way to join sliced and unsliced eEnvs
        #       Problem1: [eenv1, eenv2[:]] -> invalid (could be made valid)
        #       OK 1:     [eenv1, *eenv2[:]]
        #       Problem2: eenv1 + eenv2[:] -> invalid (could be made valid)
        #       OK 2:     eemv1[:] + eenv2[:]
    )

    log.info("done")
