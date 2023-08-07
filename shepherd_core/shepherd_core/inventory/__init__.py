""" Creates an overview for shepherd-host-machines with:
    - relevant software-versions
    - system-parameters
    - hardware-config
"""
from pathlib import Path

from pydantic.types import conlist

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
    def collect(cls):
        # one by one for more precise error messages
        pid = PythonInventory.collect().dict(exclude_unset=True, exclude_defaults=True)
        sid = SystemInventory.collect().dict(exclude_unset=True, exclude_defaults=True)
        tid = TargetInventory.collect().dict(exclude_unset=True, exclude_defaults=True)
        model = {**pid, **sid, **tid}
        return cls(**model)


class InventoryList(ShpModel):
    items: conlist(item_type=Inventory, min_items=1)

    def to_csv(self, path: Path) -> None:
        """TODO: pretty messed up (raw lists and dicts for sub-elements)
        numpy.savetxt -> too basic
        np.concatenate(content).reshape((len(content), len(content[0])))
        """
        if path.is_dir():
            path = path / "inventory.yaml"
        with open(path.as_posix(), "w") as fd:
            fd.write(", ".join(self.items[0].dict().keys()) + "\r\n")
            for item in self.items:
                content = list(item.dict().values())
                content = ["" if value is None else str(value) for value in content]
                fd.write(", ".join(content) + "\r\n")
