from .model_shepherd import ShpModel

# TODO: prototype for enabling one web-interface for all models with dynamic typecasting


class Wrapper(ShpModel):
    # initial recording
    model: str  # = model
    uid: int  # unique id, 'pk' is django-style
    fields: dict  # ShpModel
