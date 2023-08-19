from typing import List
from typing import Optional

from pydantic import ConfigDict

from ..data_models import ShpModel


class TargetInventory(ShpModel):
    cape: Optional[str] = None
    targets: List[str] = []

    model_config = ConfigDict(str_min_length=0)

    @classmethod
    def collect(cls):
        model_dict = {}

        return cls(**model_dict)
