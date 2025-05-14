"""Shows how to use inventory functionality."""

from pathlib import Path

import shepherd_core.inventory as si

pyt_inv = si.PythonInventory.collect()
print(f"PyInv: {pyt_inv}")
sys_inv = si.SystemInventory.collect()
print(f"SysInv: {sys_inv}")
tgt_inv = si.TargetInventory.collect()
print(f"TgtInv: {tgt_inv}")


inv = si.Inventory.collect()
print(f"Complete Inventory: {inv}")
inv.to_file("inventory.yaml", minimal=True, comment="just a test")

inl = si.InventoryList(elements=[inv])
inl.to_csv(Path(__file__).parent / "inventory.csv")
