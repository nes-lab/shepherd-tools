"""Base-Model for all content."""

from datetime import datetime
from typing import Annotated
from uuid import uuid4

from pydantic import Field
from pydantic import StringConstraints
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.version import version as core_ver

from .shepherd import ShpModel

# constr -> to_lower=True, max_length=16, regex=r"^[\w]+$"
# ⤷ Regex = AlphaNum
IdInt = Annotated[int, Field(ge=0, lt=2**128)]
NameStr = Annotated[str, StringConstraints(max_length=32, pattern=r"^[^<>:;,?\"\*|\/\\]+$")]
# ⤷ Regex = FileSystem-Compatible ASCII
SafeStr = Annotated[str, StringConstraints(pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


def id_default() -> int:
    """Generate a unique ID - usable as default value.

    Note: IdInt in mongoDB can currently handle 8 bytes (16 hex-values)
    """
    return int(uuid4().hex[-15:], 16)


class ContentModel(ShpModel):
    """Base-Model for content with generalized properties."""

    id: int = Field(
        description="Unique ID",
        default_factory=id_default,
    )
    name: NameStr
    """ ⤷ name of virtual content, models can be queried by this slug."""
    description: Annotated[SafeStr | None, Field(description="Required when public")] = None
    comment: SafeStr | None = None
    created: datetime = Field(default_factory=datetime.now)
    updated_last: datetime = Field(default_factory=datetime.now)
    # TODO: add dedicated 'inherit_from' field?

    # Ownership & Access
    # TODO: remove owner & group, only needed for DB
    owner: NameStr
    group: Annotated[NameStr, Field(description="University or Subgroup")]
    visible2group: bool = False
    visible2all: bool = False

    sw_ver: str = core_ver
    """ ⤷ store core-version with content for compatibility management."""

    def __str__(self) -> str:
        return self.name

    @model_validator(mode="after")
    def content_validation(self) -> Self:
        is_visible = self.visible2group or self.visible2all
        if is_visible and self.description is None:
            raise ValueError(
                "Public instances require a description (check visible2*- and description-field)"
            )
        return self
