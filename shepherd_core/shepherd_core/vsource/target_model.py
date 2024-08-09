"""Virtual targets with different characteristics.

TODO: add more targets
  - diode
  - constant power
  - constant current
  - msp430 (const I)
  - nRF (constant power due to regulator)
  - riotee
"""

from abc import ABC
from abc import abstractmethod


class TargetABC(ABC):
    """Abstract base class for all targets."""

    @abstractmethod
    def step(self, voltage_uV: int, *, pwr_good: bool) -> float:
        """Calculate one time step and return drawn current in nA."""


class ResistiveTarget(TargetABC):
    """Predictable target for matching the real world."""

    def __init__(self, resistance_Ohm: float, *, controlled: bool = False) -> None:
        self.r_Ohm = resistance_Ohm
        self.ctrl = controlled

    def step(self, voltage_uV: int, *, pwr_good: bool) -> float:
        if pwr_good or not self.ctrl:
            return 1e3 * voltage_uV / self.r_Ohm

        return 0
