"""Hardware related inventory model."""

from collections.abc import Sequence
from typing import Optional

from pydantic import ConfigDict
from typing_extensions import Self

from shepherd_core.data_models import ShpModel


class TargetInventory(ShpModel):
    """Hardware related inventory model."""

    cape: Optional[str] = None
    targets: Sequence[str] = ()

    model_config = ConfigDict(str_min_length=0)

    @classmethod
    def collect(cls) -> Self:
        model_dict = {}

        return cls(**model_dict)
