from pydantic import PositiveInt
from pydantic import constr

from .model_shepherd import ShpModel

# TODO: prototype for enabling one web-interface for all models with dynamic typecasting


class Wrapper(ShpModel):
    # initial recording
    model: constr(max_length=32)  # = model
    uid: PositiveInt  # unique id, 'pk' is django-style
    fields: dict  # ShpModel
