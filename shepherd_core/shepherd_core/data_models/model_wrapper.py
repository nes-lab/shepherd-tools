from .model_shepherd import ShpModel
from pydantic import conint

# TODO: prototype for enabling one web-interface for all models with dynamic typecasting


class Wrapper(ShpModel):
    # initial recording
    type: str  # = model
    uid: int  # unique id
    parameters: ShpModel
