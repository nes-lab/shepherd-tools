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
        if resistance_Ohm < 1e-3:
            raise ValueError("Resistance must be greater than 1e-3 Ohm.")
        self.r_kOhm = 1e-3 * resistance_Ohm
        self.ctrl = controlled

    def step(self, voltage_uV: int, *, pwr_good: bool) -> float:
        if pwr_good or not self.ctrl:
            return voltage_uV / self.r_kOhm  # = nA
        return 0


class ConstantCurrentTarget(TargetABC):
    """Recreate simple MCU without integrated regulator."""

    def __init__(self, i_active_A: float, i_sleep_A: float = 0) -> None:
        if i_active_A <= 0 or i_sleep_A <= 0:
            raise ValueError("Current must be greater than 0.")
        self.i_active_nA = 1e9 * i_active_A
        self.i_sleep_nA = 1e9 * i_sleep_A

    def step(self, voltage_uV: int, *, pwr_good: bool) -> float:  # noqa: ARG002
        return self.i_active_nA if pwr_good else self.i_sleep_nA


class ConstantPowerTarget(TargetABC):
    """Recreate MCU with integrated regulator."""

    def __init__(self, p_active_W: float, p_sleep_W: float = 0) -> None:
        if p_active_W <= 0 or p_sleep_W <= 0:
            raise ValueError("Power must be greater than 0.")
        self.p_active_fW = 1e15 * p_active_W
        self.p_sleep_fW = 1e15 * p_sleep_W

    def step(self, voltage_uV: int, *, pwr_good: bool) -> float:
        return (self.p_active_fW if pwr_good else self.p_sleep_fW) / voltage_uV  # = nA
