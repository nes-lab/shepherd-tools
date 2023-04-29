from pydantic import conint
from pydantic import constr

from .shepherd import ShpModel


class Wrapper(ShpModel):
    """Prototype for enabling one web-interface for all models with dynamic typecasting"""

    # initial recording
    model: constr(max_length=32)
    # ⤷ model-name
    id: conint(ge=0)  # noqa: A003
    # ⤷ unique id, 'pk' is django-style
    fields: dict  # ShpModel
