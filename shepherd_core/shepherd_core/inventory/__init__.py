"""Creates an overview for shepherd-host-machines.

This will collect:
- relevant software-versions
- system-parameters
- hardware-config.
"""

from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Annotated
from typing import final

from pydantic import Field
from typing_extensions import Self

from shepherd_core.data_models import ShpModel

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


@final
class Inventory(PythonInventory, SystemInventory, TargetInventory):
    """Complete inventory for one device.

    Has all child-parameters.
    """

    hostname: str
    created: datetime

    @classmethod
    def collect(cls) -> Self:
        # one by one for more precise error messages
        # NOTE: system is first, as it must take a precise timestamp
        sid = SystemInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        pid = PythonInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        tid = TargetInventory.collect().model_dump(exclude_unset=True, exclude_defaults=True)
        model = {**pid, **sid, **tid}
        # make important metadata available at root level
        model["created"] = sid["timestamp"]
        model["hostname"] = sid["hostname"]
        return cls(**model)


class InventoryList(ShpModel):
    """Collection of inventories for several devices."""

    elements: Annotated[list[Inventory], Field(min_length=1)]

    def to_csv(self, path: Path) -> None:
        """Generate a CSV.

        TODO: pretty messed up (raw lists and dicts for sub-elements)
        numpy.savetxt -> too basic
        np.concatenate(content).reshape((len(content), len(content[0]))).
        """
        if path.is_dir():
            path /= "inventory.yaml"
        with path.resolve().open("w") as fd:
            fd.write(", ".join(self.elements[0].model_dump().keys()) + "\r\n")
            for item in self.elements:
                content = list(item.model_dump().values())
                content = ["" if value is None else str(value) for value in content]
                fd.write(", ".join(content) + "\r\n")

    def warn(self) -> dict:
        warnings = {}
        ts_earl = min(e_.created.timestamp() for e_ in self.elements)
        for e_ in self.elements:
            if e_.uptime > timedelta(hours=30).total_seconds():
                warnings["uptime"] = f"[{e_.hostname}] restart is recommended"
            if (e_.created.timestamp() - ts_earl) > 10:
                warnings["time_delta"] = f"[{e_.hostname}] time-sync has failed"

        # turn  dict[hostname][type] = val
        # to    dict[type][val] = list[hostnames]
        inp_ = {
            e_.hostname: e_.model_dump(exclude_unset=True, exclude_defaults=True)
            for e_ in self.elements
        }
        result = {}
        for host_, types_ in inp_.items():
            for type_, val_ in types_.items():
                if type_ not in result:
                    result[type_] = {}
                if val_ not in result[type_]:
                    result[type_][val_] = []
                result[type_][val_].append(host_)
        rescnt = {key_: len(val_) for key_, val_ in result.items()}
        t_unique = [
            "h5py",
            "numpy",
            "pydantic",
            "python",
            "shepherd_core",
            "shepherd_sheep",
            "yaml",
            "zstandard",
        ]
        for key_ in t_unique:
            if rescnt[key_] > 1:
                warnings[key_] = f"[{key_}] VersionMismatch - {result[key_]}"

        # TODO: finish with more potential warnings
        return warnings
