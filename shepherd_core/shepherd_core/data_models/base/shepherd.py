"""Shepherds base-model that brings a lot of default functionality."""

import hashlib
import pickle
from collections.abc import Generator
from pathlib import Path
from typing import Any
from typing import final

import ryaml
from pydantic import BaseModel
from pydantic import ConfigDict
from typing_extensions import Self

from .timezone import local_now
from .wrapper import Wrapper


def path_to_str(old: dict) -> dict:
    r"""Allow platform-independent pickling of ShpModel.

    Helper Fn
    Posix-Paths (/xyz/abc) in WindowsPath gets converted to \\xyz\\abc when exported
    intended usage: pickle.dump(path_to_str(model.model_dump()))
    """
    new: dict = {}
    for key, value in old.items():
        if isinstance(value, Path):
            new[key] = value.as_posix().replace("\\", "/")
        elif isinstance(value, dict):
            new[key] = path_to_str(value)
        else:
            new[key] = value
    return new


class ShpModel(BaseModel):
    """Pre-configured Pydantic Base-Model (specifically for shepherd).

    Inheritable Features:
    - constant / frozen, hashable .get_hash()
    - safe / limited custom types
    - string-representation str(ShpModel)
    - accessible as class (model.var) and dict (model[var])
    - yaml-support with type-safe .from_file() & .to_file()
        - stores minimal set (filters out unset & default parameters)
    - schema cls.schema() can also be stored to yaml with .schema_to_file()
    """

    model_config = ConfigDict(
        frozen=True,  # -> const after creation, hashable! but currently manually with .get_hash()
        extra="forbid",  # no unnamed attributes allowed
        validate_default=True,
        validate_assignment=True,  # not relevant for the frozen model
        str_min_length=1,  # force more meaningful descriptors,
        # ⤷ TODO: was 4 but localizing constraints works different with pydantic2
        #       - might be solvable with "use_enum_values=True"
        str_max_length=512,
        # ⤷ local str-length constraints overrule global ones!
        str_strip_whitespace=True,  # strip leading & trailing whitespaces
        use_enum_values=True,  # cleaner export of enum-parameters
        allow_inf_nan=False,  # float without +-inf or NaN
        # defer_build=True, possible speedup -> but it triggers a bug
    )

    def __repr__(self) -> str:
        """string-representation allows print(model)."""
        name = type(self).__name__
        content = self.model_dump(mode="json", exclude_unset=True, exclude_defaults=True)
        return f"{name}({content})"

    def __str__(self) -> str:
        """string-representation allows str(model) and will be in YAML-format."""
        return ryaml.dumps(
            self.model_dump(mode="json", exclude_unset=True, exclude_defaults=True),
        )

    def __getitem__(self, key: Any) -> Any:
        """Allow dict access like model["key"].

        in addition to model.key.
        """
        if isinstance(key, str):
            return self.__getattribute__(key)
        msg = f"Unknown key '{key}' used when selecting from Model."
        raise IndexError(msg)

    def __contains__(self, item: str) -> bool:
        """Allow checks like 'x in YClass'."""
        return item in self.model_dump().keys()  # noqa: SIM118
        # more correct, but probably slower than hasattr

    def keys(self):  # noqa: ANN201
        """Fn of dict."""
        return self.model_dump().keys()  # TODO: there is an easier way

    def items(self) -> Generator[tuple, None, None]:
        """Fn of dict."""
        for key in self.keys():
            yield key, self.__getattribute__(key)

    @final
    @classmethod
    def schema_to_file(cls, path: str | Path) -> None:
        """Store schema to yaml (for frontend-generators)."""
        model_dict = cls.model_json_schema()
        with Path(path).resolve().with_suffix(".yaml").open("w", encoding="utf-8") as fp:
            ryaml.dump(fp, model_dict)

    @final
    def to_file(
        self,
        path: str | Path,
        comment: str | None = None,
        *,
        minimal: bool = True,
        use_pickle: bool = False,
    ) -> Path:
        """Store data to yaml in a wrapper.

        minimal: stores minimal set (filters out unset & default parameters)
        pickle: uses pickle to serialize data, on BBB >100x faster for large files
        comment: documentation.
        """
        model_wrap = Wrapper(
            datatype=type(self).__name__,
            comment=comment,
            created=local_now(),
            parameters=self.model_dump(exclude_unset=minimal),
        )
        if use_pickle:
            # TODO: pickle can just dump the original model
            model_dict = model_wrap.model_dump(exclude_unset=minimal, exclude_defaults=minimal)
            model_serial = pickle.dumps(path_to_str(model_dict))
            model_path = Path(path).resolve().with_suffix(".pickle")
        else:
            model_dict = model_wrap.model_dump(
                mode="json", exclude_unset=minimal, exclude_defaults=minimal
            )
            model_serial = ryaml.dumps(model_dict)
            model_path = Path(path).resolve().with_suffix(".yaml")
        # TODO: handle directory

        if not model_path.parent.exists():  # TODO: can be restructured to allow ryaml.dump()
            model_path.parent.mkdir(parents=True)
        with model_path.open(
            "wb" if use_pickle else "w",
            encoding=None if use_pickle else "utf-8",
        ) as f:
            f.write(model_serial)
        return model_path

    @final
    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Load from YAML or pickle file."""
        path: Path = Path(path)
        if not Path(path).exists():
            raise FileNotFoundError
        if path.suffix.lower() == ".pickle":
            with Path(path).open("rb") as shp_file:
                shp_dict = pickle.load(shp_file)  # noqa: S301
        else:
            with Path(path).open(encoding="utf-8") as shp_file:
                shp_dict = ryaml.load(shp_file)
        shp_wrap = Wrapper(**shp_dict)
        if shp_wrap.datatype != cls.__name__:
            raise ValueError("Model in file does not match the actual Class")
        return cls(**shp_wrap.parameters)

    @final
    def get_hash(self) -> str:
        return hashlib.sha3_224(str(self.model_dump()).encode("utf-8")).hexdigest()
