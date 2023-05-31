import hashlib
import pathlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

import yaml
from pydantic import BaseModel
from pydantic import Extra

from .wrapper import Wrapper


def repr_str(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(pathlib.PosixPath, repr_str)
yaml.add_representer(pathlib.WindowsPath, repr_str)
yaml.add_representer(pathlib.Path, repr_str)


class ShpModel(BaseModel):
    """Pre-configured Pydantic Base-Model (specifically for shepherd)

    Inheritable Features:
    - constant / frozen, hashable .get_hash()
    - safe / limited custom types
    - string-representation str(ShpModel)
    - accessible as class (model.var) and dict (model[var])
    - yaml-support with type-safe .from_file() & .to_file()
    - schema cls.schema() can also be stored to yaml with .dump_schema()
    """

    _min_dict: dict = {}

    class Config:
        allow_mutation = False  # const after creation?
        frozen = True  # -> hashable! but currently manually with .get_hash()
        extra = Extra.forbid  # no unnamed attributes allowed
        validate_all = True  # also checks defaults
        validate_assignment = True
        min_anystr_length = 4
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
        return str(self.dict())

    def __getitem__(self, key):
        return self.__getattribute__(key)

    @classmethod
    def dump_schema(cls, path: Union[str, Path]) -> None:
        # TODO: rename to schema_to_file(), if needed at all
        model_dict = cls.schema()
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)
        with open(Path(path).with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)

    def to_file(
        self,
        path: Union[str, Path],
        minimal: bool = False,
        comment: Optional[str] = None,
    ) -> Path:
        if minimal:
            model_dict = self._min_dict
        else:
            model_dict = self.dict()
        model_wrap = Wrapper(
            model=type(self).__name__,
            comment=comment,
            created=datetime.now(),
            parameters=model_dict,
        )
        model_yaml = yaml.dump(
            model_wrap.dict(), default_flow_style=False, sort_keys=False
        )
        model_path = Path(path).with_suffix(".yaml")
        with open(model_path, "w") as f:
            f.write(model_yaml)
        return model_path
        # TODO: it would be useful to store a minimal set
        #    - current dict cleaned from default values
        #    - better: the init-args (probably name or id)
        #  -> test, non-functioning atm

    @classmethod
    def from_file(cls, path: Union[str, Path]):
        with open(Path(path)) as shp_file:
            shp_dict = yaml.safe_load(shp_file)
        shp_wrap = Wrapper(**shp_dict)
        if shp_wrap.model != cls.__name__:
            raise ValueError("Model in file does not match the requirement")
        return cls(**shp_wrap.parameters)

    @classmethod  # @root_validator(pre=True, allow_reuse=True)
    def pre_snitch(cls, values):  # TODO: useless
        values["_min_dict"] = values
        return values

    def get_hash(self):
        return hashlib.sha3_224(str(self.dict()).encode("utf-8")).hexdigest()
