from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel


class ShpModel(BaseModel):
    # TODO: not needed anymore (currently)
    class Config:
        title = ""  # example: Virtual Source MinDef"
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        validate_assignment = True
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces
        # TODO: according to
        #   - https://docs.pydantic.dev/usage/schema/#field-customization
        #   - https://docs.pydantic.dev/usage/model_config/
        # "fields["name"].description = ... should be usable to modify model

    @classmethod
    def dump_schema(cls, path: Union[str, Path]):
        model_dict = cls.schema()
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)
        with open(Path(path).with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)

    def dump_dict(self, path: Union[str, Path]):
        model_dict = self.dict()
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)
        with open(Path(path).with_suffix(".yaml"), "w") as f:
            f.write(model_yaml)
