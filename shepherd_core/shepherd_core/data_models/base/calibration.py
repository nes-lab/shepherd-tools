from typing import TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import PositiveFloat

from .shepherd import ShpModel

T_calc = TypeVar("T_calc", NDArray[np.float64], float)


class CalibrationPair(ShpModel):
    """SI-value [SI-Unit] = raw-value * gain + offset"""

    gain: PositiveFloat
    offset: float = 0

    def raw_to_si(self, values_raw: T_calc) -> T_calc:
        """Helper to convert between physical units and raw unsigned integers"""
        values_si = values_raw * self.gain + self.offset
        if isinstance(values_si, np.ndarray):
            values_si[values_si < 0.0] = 0.0
            # if pyright still complains, cast with .astype(float)
        else:
            values_si = float(max(values_si, 0.0))
        return values_si

    def si_to_raw(self, values_si: T_calc) -> T_calc:
        """Helper to convert between physical units and raw unsigned integers"""
        values_raw = (values_si - self.offset) / self.gain
        if isinstance(values_raw, np.ndarray):
            values_raw[values_raw < 0.0] = 0.0
        else:
            values_raw = max(values_raw, 0.0)
        return values_raw


class CalibrationSeries(ShpModel):
    voltage: CalibrationPair = CalibrationPair(gain=3 * 1e-9)
    # ⤷ default allows 0 - 12 V in 3 nV-Steps
    current: CalibrationPair = CalibrationPair(gain=250 * 1e-12)
    # ⤷ default allows 0 - 1 A in 250 pA - Steps
    time: CalibrationPair = CalibrationPair(gain=1e-9)
    # ⤷ default allows nanoseconds


class CalibrationEmulator(ShpModel):
    pass
