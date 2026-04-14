"""Current implementation of a file-based database."""

import copy
import pickle
from collections.abc import Iterable
from collections.abc import Mapping
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

import ryaml
from pydantic import validate_call
from typing_extensions import Self
from typing_extensions import deprecated

from shepherd_core.data_models.base.timezone import local_now
from shepherd_core.data_models.base.timezone import local_tz
from shepherd_core.data_models.base.wrapper import Wrapper
from shepherd_core.logger import log

from .cache_path import cache_user_path

# Proposed field-name:
# - inheritance
# - inherit_from  <-- current choice
# - inheritor
# - hereditary
# - based_on


class Fixture:
    """Current implementation of a file-based database."""

    def __init__(self, model_type: str) -> None:
        self.model_type: str = model_type.lower()
        self.elements_by_name: dict[str, dict[str, Any]] = {}
        self.elements_by_id: dict[int, dict[str, Any]] = {}
        self.update_iterator(reset=True)

    def insert_verified(self, data: Wrapper) -> None:
        # ⤷ TODO: could get easier
        #    - when not model_name but class used
        #    - use doubleref name->id->data (saves RAM)
        if data.datatype.lower() != self.model_type.lower():
            return
        if "name" not in data.parameters:
            return  # name is mandatory
        name = str(data.parameters["name"]).lower()
        data_model = data.parameters
        self.elements_by_name[name] = data_model
        if "id" in data.parameters:  # ID is optional
            id_ = data.parameters["id"]
            self.elements_by_id[id_] = data_model
        self.update_iterator()

    def insert_raw(self, data_model: dict) -> None:
        """Faster version, with less validation."""
        self.elements_by_name[str(data_model["name"]).lower()] = data_model
        if "id" in data_model:  # ID is optional
            self.elements_by_id[data_model["id"]] = data_model

    def update_iterator(self, *, reset: bool = False) -> None:
        if reset:
            self._iter_index: int = 0
        self._iter_list: list[dict[str, Any]] = list(self.elements_by_name.values())

    def __getitem__(self, key: str | int) -> dict[str, Any]:
        original_key = key
        if isinstance(key, str):
            key = key.lower()
            if key in self.elements_by_name:
                return self.elements_by_name[key]
            if key.isdigit():
                key = int(key)
        if key in self.elements_by_id:
            return self.elements_by_id[int(key)]
        msg = f"{self.model_type} '{original_key}' not found!"
        raise ValueError(msg)

    def __iter__(self) -> Self:
        self._iter_index = 0
        self._iter_list = list(self.elements_by_name.values())
        return self

    def __next__(self) -> dict[str, Any]:
        if self._iter_index < len(self._iter_list):
            member = self._iter_list[self._iter_index]
            self._iter_index += 1
            return member
        raise StopIteration

    def keys(self) -> Iterable[str]:
        return self.elements_by_name.keys()

    @deprecated("ID is currently optional, so this list is NOT complete.")
    def refs(self) -> dict:
        return {i_["id"]: i_["name"] for i_ in self.elements_by_id.values()}

    def inheritance(
        self, values: dict[str, Any], chain: list[str] | None = None
    ) -> tuple[dict[str, Any], list[str]]:
        if chain is None:
            chain = []
        values = copy.copy(values)
        post_process: bool = False
        fixture_base: dict = {}
        if "inherit_from" in values:
            fixture_name = values.pop("inherit_from")
            # ⤷ will also remove entry from dict
            if "name" in values and len(chain) < 1:
                base_name = str(values.get("name"))
                if base_name in chain:
                    msg = f"Inheritance-Circle detected ({base_name} already in {chain})"
                    raise ValueError(msg)
                if base_name == fixture_name:
                    msg = f"Inheritance-Circle detected ({base_name} == {fixture_name})"
                    raise ValueError(msg)
                chain.append(base_name)
            fixture_base = copy.copy(self[fixture_name])
            log.debug("'%s' will inherit from '%s'", self.model_type, fixture_name)
            fixture_base["name"] = fixture_name
            chain.append(fixture_name)
            base_dict, chain = self.inheritance(values=fixture_base, chain=chain)
            for key, value in values.items():
                # keep previous entries
                base_dict[key] = value
            values = base_dict

        # TODO: cleanup and simplify - use fill_mode() and line up with web-interface
        elif "name" in values and str(values.get("name")).lower() in self.elements_by_name:
            fixture_name = str(values.get("name")).lower()
            fixture_base = copy.copy(self.elements_by_name[fixture_name])
            post_process = True

        elif values.get("id") in self.elements_by_id:
            id_ = values["id"]
            fixture_base = copy.copy(self.elements_by_id[id_])
            post_process = True

        if post_process:
            # last two cases need
            for key, value in values.items():
                # keep previous entries
                fixture_base[key] = value
            if "inherit_from" in fixture_base:
                # as long as this key is present this will act recursively
                chain.append(fixture_base["name"])
                values, chain = self.inheritance(values=fixture_base, chain=chain)
            else:
                values = fixture_base

        return values, chain

    @staticmethod
    def fill_model(model: Mapping, base: dict) -> dict:
        base = copy.copy(base)
        for key, value in model.items():
            # keep previous entries
            base[key] = value
        return base

    def query_id(self, _id: int) -> dict[str, Any]:
        if isinstance(_id, int) and _id in self.elements_by_id:
            return self.elements_by_id[_id]
        msg = f"Initialization of {self.model_type} by ID failed - {_id} is unknown!"
        raise ValueError(msg)

    def query_name(self, name: str) -> dict[str, Any]:
        if isinstance(name, str) and name.lower() in self.elements_by_name:
            return self.elements_by_name[name.lower()]
        msg = f"Initialization of {self.model_type} by name failed - {name} is unknown!"
        raise ValueError(msg)


def file_older_than(file: Path, delta: timedelta) -> bool:
    """Decide if file is older than a specific duration of time."""
    cutoff = local_now() - delta
    mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=local_tz())
    return mtime < cutoff


class Fixtures:
    """A collection of individual fixture-elements."""

    suffix = ".yaml"

    @validate_call
    def __init__(
        self, file_path: Path | None = None, *, reset: bool = False, validate: bool = False
    ) -> None:
        self.reset = reset
        self.components: dict[str, Fixture] = {}

        cache_file = cache_user_path / "fixtures.pickle"
        sheep_detect = Path("/lib/firmware/am335x-pru0-fw").exists()

        if (
            sheep_detect
            and cache_file.exists()
            and not file_older_than(cache_file, timedelta(hours=24))
            and not self.reset
        ):
            # speedup by loading from cache
            # TODO: also add version as criterion
            with cache_file.open("rb", buffering=-1) as fd:
                self.components = pickle.load(fd)  # noqa: S301
            log.debug(" -> found & used pickled fixtures")
        else:
            if not isinstance(file_path, Path):
                file_path: Path = Path(__file__).parent.parent.resolve() / "data_models"
            else:
                validate = True  # expect untested data

            if file_path.is_file():
                files = [file_path]
            elif file_path.is_dir():
                files = list(
                    file_path.glob("**/*" + self.suffix)
                )  # for py>=3.12: case_sensitive=False
                log.debug(" -> got %s %s-files", len(files), self.suffix)
            else:
                raise ValueError("Path must either be file or directory (or empty)")

            for file in files:
                if validate:
                    self.validate_file(file)
                else:
                    self._insert_file(file)

            if len(self.components) < 1:
                log.error(f"No fixture-components found at {file_path.as_posix()}")
            elif sheep_detect:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with cache_file.open("wb", buffering=-1) as fd:
                    pickle.dump(self.components, fd)
        for ckey in self.components:
            self.components[ckey].update_iterator(reset=True)

    def _insert_file(self, file: Path) -> None:
        with file.open(encoding="utf-8-sig") as fd:
            fixtures = ryaml.load(fd)
        for data_wrap in fixtures:
            # this is a faster version .insert_model()
            if not isinstance(data_wrap, dict):
                continue
            fix_type = str(data_wrap["datatype"]).lower()
            if self.components.get(fix_type) is None:
                self.components[fix_type] = Fixture(model_type=fix_type)
            self.components[fix_type].insert_raw(data_wrap["parameters"])

    def validate_file(self, file: Path) -> None:
        """Slower version of ._insert_file() with more checks.

        This allows to verify all fixtures in unittests.
        """
        with file.open(encoding="utf-8-sig") as fd:
            fixtures = ryaml.load(fd)
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                continue
            fix_wrap = Wrapper(**fixture)
            self.insert_model(fix_wrap)

    def insert_model(self, data: Wrapper) -> None:
        """Delegate model to correct component."""
        fix_type = data.datatype.lower()
        if self.components.get(fix_type) is None:
            self.components[fix_type] = Fixture(model_type=fix_type)
        self.components[fix_type].insert_verified(data)

    def __getitem__(self, key: str) -> Fixture:
        key = key.lower()
        if key in self.components:
            return self.components[key]
        msg = f"Component '{key}' not found!"
        raise KeyError(msg)

    def keys(self) -> Iterable[str]:
        return self.components.keys()

    def to_file(self, file: Path) -> None:
        msg = f"TODO (val={file})"
        raise NotImplementedError(msg)
