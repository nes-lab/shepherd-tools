from abc import ABC
from abc import abstractmethod


class TargetABC(ABC):
    @abstractmethod
    def step(self, voltage_uV: int, pwr_good: bool) -> float:
        """Calculate one time step and return drawn current in nA"""


class ResistiveTarget(TargetABC):
    def __init__(self, resistance_Ohm: float, *, controlled: bool = False):
        self.r_Ohm = resistance_Ohm
        self.ctrl = controlled

    def step(self, voltage_uV: int, pwr_good: bool) -> float:
        if pwr_good or not self.ctrl:
            return 1e3 * voltage_uV / self.r_Ohm
        else:
            return 0


# TODO: add more targets
#   - diode
#   - constant power
#   - constant current
#   - msp430
#   - nRF (constant power due to regulator)
#   - riotee
