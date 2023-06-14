import hashlib
import pathlib
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Optional
from typing import Union

import yaml
from pydantic import BaseModel
from pydantic import Extra
from yaml import SafeDumper

from .wrapper import Wrapper


def path2str(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data.as_posix()))


def time2int(dumper, data):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:int", str(int(data.total_seconds()))
    )


yaml.add_representer(pathlib.PosixPath, path2str, SafeDumper)
yaml.add_representer(pathlib.WindowsPath, path2str, SafeDumper)
yaml.add_representer(pathlib.Path, path2str, SafeDumper)
yaml.add_representer(timedelta, time2int, SafeDumper)


class ShpModel(BaseModel):
    """Pre-configured Pydantic Base-Model (specifically for shepherd)

    Inheritable Features:
    - constant / frozen, hashable .get_hash()
    - safe / limited custom types
    - string-representation str(ShpModel)
    - accessible as class (model.var) and dict (model[var])
    - yaml-support with type-safe .from_file() & .to_file()
        - stores minimal set (filters out unset & default parameters)
    - schema cls.schema() can also be stored to yaml with .schema_to_file()
    """

    class Config:
        allow_mutation = False  # const after creation
        frozen = True  # -> hashable! but currently manually with .get_hash()
        extra = Extra.forbid  # no unnamed attributes allowed
        validate_all = True  # also checks defaults
        validate_assignment = True  # not relevant for the frozen model
        min_anystr_length = 4  # force more meaningful descriptors
        max_anystr_length = 512
        # ⤷ local str-length constraints overrule global ones!
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces
        use_enum_values = True  # cleaner export of enum-parameters
        allow_inf_nan = False  # float without +-inf or NaN
        underscore_attrs_are_private = True  # allows using them
        # Options:
        # - https://docs.pydantic.dev/usage/schema/#field-customization
        # - https://docs.pydantic.dev/usage/model_config/
        # "fields["name"].description = ... should be usable to modify model

    def __repr__(self) -> str:
        """string-representation allows print(model)"""
        return str(self.dict(exclude_unset=True, exclude_defaults=True))

    def __getitem__(self, key):
        """allows dict access -> model["key"], in addition to model.key"""
        return self.__getattribute__(key)

    @classmethod
    def schema_to_file(cls, path: Union[str, Path]) -> None:
        """store schema to yaml (for frontend-generators)"""
        model_dict = cls.schema()
        model_yaml = yaml.safe_dump(
            model_dict, default_flow_style=False, sort_keys=False
        )
        with open(Path(path).resolve().with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)

    def to_file(
        self,
        path: Union[str, Path],
        minimal: bool = True,
        comment: Optional[str] = None,
    ) -> Path:
        """store data to yaml in a wrapper
        minimal: stores minimal set (filters out unset & default parameters)
        comment: documentation
        """
        model_dict = self.dict(exclude_unset=minimal, exclude_defaults=minimal)
        #
        model_wrap = Wrapper(
            datatype=type(self).__name__,
            comment=comment,
            created=datetime.now(),
            parameters=model_dict,
        )
        model_yaml = yaml.safe_dump(
            model_wrap.dict(exclude_unset=minimal, exclude_defaults=minimal),
            default_flow_style=False,
            sort_keys=False,
        )
        # TODO: handle directory
        model_path = Path(path).resolve().with_suffix(".yaml")
        with open(model_path, "w") as f:
            f.write(model_yaml)
        return model_path

    @classmethod
    def from_file(cls, path: Union[str, Path]):
        """load from yaml"""
        with open(Path(path).resolve()) as shp_file:
            shp_dict = yaml.safe_load(shp_file)
        shp_wrap = Wrapper(**shp_dict)
        if shp_wrap.datatype != cls.__name__:
            raise ValueError("Model in file does not match the requirement")
        return cls(**shp_wrap.parameters)

    def get_hash(self):
        return hashlib.sha3_224(str(self.dict()).encode("utf-8")).hexdigest()
