import hashlib
import pathlib
from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel
from pydantic import Extra


def repr_str(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(pathlib.PosixPath, repr_str)
yaml.add_representer(pathlib.WindowsPath, repr_str)
yaml.add_representer(pathlib.Path, repr_str)


class ShpModel(BaseModel):
    """Pre-configured Pydantic Base-Model (specifically for shepherd)"""

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
        use_enum_values = True  # cleaner export of enum-fields
        allow_inf_nan = False  # float without +-inf or NaN
        underscore_attrs_are_private = True  # allows using them

        # Options:
        # - https://docs.pydantic.dev/usage/schema/#field-customization
        # - https://docs.pydantic.dev/usage/model_config/
        # "fields["name"].description = ... should be usable to modify model

    @classmethod
    def dump_schema(cls, path: Union[str, Path]):
        model_dict = cls.schema()
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)
        with open(Path(path).with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)

    def dump_dict(self, path: Union[str, Path], minimal: bool = False):
        if minimal:
            model_dict = self._min_dict
        else:
            model_dict = self.dict()
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)
        with open(Path(path).with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)
        # TODO: it would be useful to store a minimal set
        #    - current dict cleaned from default values
        #    - better: the init-args (probably name or id)
        #  -> test, non-functioning atm

    @classmethod  # @root_validator(pre=True, allow_reuse=True)
    def pre_snitch(cls, values):
        values["_min_dict"] = values
        return values

    def get_hash(self):
        return hashlib.sha3_224(str(self.dict()).encode("utf-8")).hexdigest()
