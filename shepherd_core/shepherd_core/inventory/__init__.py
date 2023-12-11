"""Creates an overview for shepherd-host-machines with:
- relevant software-versions
- system-parameters
- hardware-config
"""
from pathlib import Path
from typing import List

from pydantic import Field
from typing_extensions import Annotated
from typing_extensions import Self

from ..data_models import ShpModel
from .python import PythonInventory
from .system import SystemInventory
from .target import TargetInventory

__all__ = [
    "Inventory",
    "InventoryList",
    "PythonInventory",
    "SystemInventory",
    "TargetInventory",
]


class Inventory(PythonInventory, SystemInventory, TargetInventory):
    # has all child-parameters

    @classmethod
    def collect(cls) -> Self:
        # one by one for more precise error messages
        pid = PythonInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        sid = SystemInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        tid = TargetInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        model = {**pid, **sid, **tid}
        return cls(**model)


class InventoryList(ShpModel):
    elements: Annotated[List[Inventory], Field(min_length=1)]

    def to_csv(self, path: Path) -> None:
        """TODO: pretty messed up (raw lists and dicts for sub-elements)
        numpy.savetxt -> too basic
        np.concatenate(content).reshape((len(content), len(content[0])))
        """
        if path.is_dir():
            path = path / "inventory.yaml"
        with path.resolve().open("w") as fd:
            fd.write(", ".join(self.elements[0].model_dump().keys()) + "\r\n")
            for item in self.elements:
                content = list(item.model_dump().values())
                content = ["" if value is None else str(value) for value in content]
                fd.write(", ".join(content) + "\r\n")
