"""Shows how to use inventory functionality."""

from pathlib import Path

import shepherd_core.inventory as si

pi = si.PythonInventory.collect()
print(f"PyInv: {pi}")
si = si.SystemInventory.collect()
print(f"SysInv: {si}")
ti = si.TargetInventory.collect()
print(f"TgtInv: {ti}")


inv = si.Inventory.collect()
print(f"Complete Inventory: {inv}")
inv.to_file("inventory.yaml", minimal=True, comment="just a test")

inl = si.InventoryList(elements=[inv])
inl.to_csv(Path(__file__).parent / "inventory.csv")
