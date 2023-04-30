from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import constr
from pydantic import root_validator

from .shepherd import ShpModel

id_str = constr(to_lower=True, max_length=16, regex=r"^[\w]*$")
name_str = constr(max_length=32, regex=r"^[ -~]*$")
# ⤷ TODO: maybe this should be more limited to file-system-chars
safe_str = constr(regex=r"^[ -~]*$")


class ContentModel(ShpModel):
    # General Properties
    id: id_str = Field(description="Unique ID (AlphaNum > 4 chars)")  # noqa: A003
    name: name_str
    description: Optional[safe_str] = Field(description="Required when public")
    comment: Optional[safe_str] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access
    owner: name_str
    group: name_str = Field(description="University or Subgroup")
    visible2group: bool = False
    visible2all: bool = False

    # The Regex
    # ^[\\w]*$    AlphaNum
    # ^[ -~]*$    All Printable ASCII-Characters with Space

    @root_validator(pre=False)
    def content_validation(cls, values: dict):
        is_visible = values["visible2group"] or values["visible2all"]
        if is_visible and values["description"] is None:
            raise ValueError(
                "Public instances require a description "
                "(check open2*- and description-field)"
            )
        return values
