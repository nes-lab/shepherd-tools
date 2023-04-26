from pydantic import conint
from pydantic import constr

from .model_shepherd import ShpModel

# TODO: prototype for enabling one web-interface for all models with dynamic typecasting


class Wrapper(ShpModel):
    # initial recording
    model: constr(max_length=32)  # = model
    uid: conint(ge=0)  # unique id, 'pk' is django-style
    fields: dict  # ShpModel
