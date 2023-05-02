import hashlib
from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import conint
from pydantic import constr
from pydantic import root_validator

from .shepherd import ShpModel

# constr -> to_lower=True, max_length=16, regex=r"^[\w]+$"
# ⤷ Regex = AlphaNum
id_int = conint(ge=0, lt=2**128)
name_str = constr(max_length=32, regex=r'^[^<>:;,?"*|]+$')
# ⤷ Regex = FS-Compatible ASCII
safe_str = constr(regex=r"^[ -~]+$")
# ⤷ Regex = All Printable ASCII-Characters with Space


def id_default() -> int:
    time_stamp = str(datetime.now()).encode("utf-8")
    time_hash = hashlib.sha3_224(time_stamp).hexdigest()[-16:]
    return int(time_hash, 16)


class ContentModel(ShpModel):
    # General Properties
    id: id_int = Field(  # noqa: A003
        description="Unique ID",
        default_factory=id_default,
    )
    name: name_str
    description: Optional[safe_str] = Field(description="Required when public")
    comment: Optional[safe_str] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access
    owner: name_str
    group: name_str = Field(description="University or Subgroup")
    visible2group: bool = False
    visible2all: bool = False

    @root_validator(pre=False)
    def content_validation(cls, values: dict):
        is_visible = values["visible2group"] or values["visible2all"]
        if is_visible and values["description"] is None:
            raise ValueError(
                "Public instances require a description "
                "(check visible2*- and description-field)"
            )
        return values
