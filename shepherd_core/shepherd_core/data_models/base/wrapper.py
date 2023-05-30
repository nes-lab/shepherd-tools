from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import conint
from pydantic import constr

SafeStrClone = constr(regex=r"^[ -~]+$")
# ⤷ copy avoids circular import


class Wrapper(BaseModel):
    """Prototype for enabling one web- & file-interface for
    all models with dynamic typecasting
    TODO: id not needed, fields=>parameters, model=>type
    """

    model: str
    # ⤷ model-name
    id: Optional[conint(ge=0, lt=2**128)]  # noqa: A003
    # ⤷ unique id, 'pk' is django-style
    comment: Optional[SafeStrClone]
    created: Optional[datetime]
    # ⤷ Optional metadata
    fields: dict
    # ⤷ ShpModel
