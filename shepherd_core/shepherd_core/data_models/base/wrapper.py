from typing import Optional

from pydantic import BaseModel
from pydantic import conint


class Wrapper(BaseModel):
    """Prototype for enabling one web- & file-interface for
    all models with dynamic typecasting"""

    # initial recording
    model: str
    # ⤷ model-name
    id: Optional[conint(ge=0, lt=2**128)]  # noqa: A003
    # ⤷ unique id, 'pk' is django-style
    fields: dict  # ShpModel
