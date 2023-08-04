from typing import Optional

from pydantic import conlist

from ..data_models import ShpModel


class TargetInventory(ShpModel):
    cape: Optional[str] = None
    targets: conlist(item_type=str) = []

    class Config:
        min_anystr_length = 0

    @classmethod
    def collect(cls):
        model_dict = {}

        return cls(**model_dict)
