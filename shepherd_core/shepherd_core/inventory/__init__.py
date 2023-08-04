""" Creates an overview for shepherd-host-machines with:
    - relevant software-versions
    - system-parameters
    - hardware-config
"""
from .python import PythonInventory
from .system import SystemInventory
from .target import TargetInventory

__all__ = [
    "Inventory",
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
