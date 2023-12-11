import hashlib
from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic import StringConstraints
from pydantic import model_validator
from typing_extensions import Annotated
from typing_extensions import Self

from .shepherd import ShpModel
from .timezone import local_now

# constr -> to_lower=True, max_length=16, regex=r"^[\w]+$"
# ⤷ Regex = AlphaNum
IdInt = Annotated[int, Field(ge=0, lt=2**128)]
NameStr = Annotated[str, StringConstraints(max_length=32, pattern=r'^[^<>:;,?"*|\/\\]+$')]
# ⤷ Regex = FileSystem-Compatible ASCII
SafeStr = Annotated[str, StringConstraints(pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


def id_default() -> int:
    time_stamp = str(local_now()).encode("utf-8")
    time_hash = hashlib.sha3_224(time_stamp).hexdigest()[-16:]
    return int(time_hash, 16)


class ContentModel(ShpModel):
    # General Properties
    id: IdInt = Field(  # noqa: A003
        description="Unique ID",
        default_factory=id_default,
    )
    name: NameStr
    description: Annotated[Optional[SafeStr], Field(description="Required when public")] = None
    comment: Optional[SafeStr] = None
    created: datetime = Field(default_factory=datetime.now)

    # Ownership & Access
    owner: NameStr
    group: Annotated[NameStr, Field(description="University or Subgroup")]
    visible2group: bool = False
    visible2all: bool = False

    # TODO: we probably need to remember the lib-version for content &| experiment

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
