from pathlib import Path

import pytest

from shepherd_core.inventory import Inventory
from shepherd_core.inventory import InventoryList
from shepherd_core.inventory import PythonInventory
from shepherd_core.inventory import SystemInventory
from shepherd_core.inventory import TargetInventory


@pytest.mark.parametrize("inv", [PythonInventory, SystemInventory, TargetInventory, Inventory])
def test_collect_data(inv: Inventory) -> None:
    inv.collect()


def test_inventorize(tmp_path: Path) -> None:
    inv = Inventory.collect()
    inl = InventoryList(elements=[inv])
    inl.to_csv(tmp_path / "some.csv")
