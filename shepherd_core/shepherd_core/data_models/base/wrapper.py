"""Wrapper-related ecosystem for transferring models."""

from datetime import datetime
from typing import Annotated
from typing import final

from pydantic import BaseModel
from pydantic import StringConstraints

from shepherd_core.version import version

SafeStrClone = Annotated[str, StringConstraints(pattern=r"^[ -~]+$")]
# ⤷ copy avoids circular import


@final
class Wrapper(BaseModel):
    """Generalized web- & file-interface for all models with dynamic typecasting."""

    datatype: str
    """ ⤷ model-name"""
    comment: SafeStrClone | None = None
    created: datetime | None = None
    """ ⤷ Optional metadata"""
    lib_ver: str | None = version
    """ ⤷ for debug-purposes and later compatibility-checks"""
    parameters: dict
    """ ⤷ ShpModel"""
