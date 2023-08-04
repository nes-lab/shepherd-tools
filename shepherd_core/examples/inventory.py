from shepherd_core.inventory import Inventory
from shepherd_core.inventory import PythonInventory
from shepherd_core.inventory import SystemInventory
from shepherd_core.inventory import TargetInventory

pi = PythonInventory.collect()
print(f"PyInv: {pi}")
si = SystemInventory.collect()
print(f"SysInv: {si}")
ti = TargetInventory.collect()
print(f"TgtInv: {ti}")


inv = Inventory.collect()
print(f"Complete Inventory: {inv}")
inv.to_file("inventory.yaml", minimal=True, comment="just a test")
