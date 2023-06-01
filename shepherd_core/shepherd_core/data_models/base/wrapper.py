from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import constr

SafeStrClone = constr(regex=r"^[ -~]+$")
# ⤷ copy avoids circular import


class Wrapper(BaseModel):
    """Prototype for enabling one web- & file-interface for
    all models with dynamic typecasting
    """

    model: str
    # ⤷ model-name
    comment: Optional[SafeStrClone]
    created: Optional[datetime]
    # ⤷ Optional metadata
    parameters: dict
    # ⤷ ShpModel
