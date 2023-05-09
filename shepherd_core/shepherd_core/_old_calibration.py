""" Helper-FNs to convert values between raw/int and physical si-units

"""
from typing import Dict
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

# TODO: build
#  - unit-converter-class that takes cal-pairs (gain, offset)
#  - cal-class that takes dict of pairs and builds complete converter

cal_default: Dict[str, Dict[str, float]] = {
    "voltage": {"gain": 3 * 1e-9, "offset": 0.0},  # allows 0 - 12 V in 3 nV-Steps
    "current": {"gain": 250 * 1e-12, "offset": 0.0},  # allows 0 - 1 A in 250 pA - Steps
    "time": {"gain": 1e-9, "offset": 0.0},
    # SI-value [SI-Unit] = raw-value * gain + offset
}

T_calc = TypeVar("T_calc", NDArray[np.float64], float)


def raw_to_si(values_raw: T_calc, cal: Dict[str, float]) -> T_calc:
    """Helper to convert between physical units and raw unsigned integers

    :param values_raw: number or numpy array with raw values
    :param cal: calibration-dict with entries for gain and offset
    :return: converted number or array
    """
    values_si = values_raw * cal["gain"] + cal["offset"]
    if isinstance(values_si, np.ndarray):
        values_si[values_si < 0.0] = 0.0
        # if pyright still complains, cast with .astype(float)
    else:
        values_si = float(max(values_si, 0.0))
    return values_si


def si_to_raw(values_si: T_calc, cal: Dict[str, float]) -> T_calc:
    """Helper to convert between physical units and raw unsigned integers

    :param values_si: number or numpy array with values in physical units
    :param cal: calibration-dict with entries for gain and offset
    :return: converted number or array
    """
    values_raw = (values_si - cal["offset"]) / cal["gain"]
    if isinstance(values_raw, np.ndarray):
        values_raw[values_raw < 0.0] = 0.0
    else:
        values_raw = max(values_raw, 0.0)
    return values_raw
