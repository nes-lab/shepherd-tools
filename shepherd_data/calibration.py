""" Helper-FNs to convert values between raw/int and physical si-units

"""
from typing import Union
import numpy as np


# SI-value [SI-Unit] = raw-value * gain + offset
cal_default: dict[str, dict] = {
    "voltage": {"gain": 3 * 1e-9, "offset": 0.0},  # allows 0 - 12 V in 3 nV-Steps
    "current": {"gain": 250 * 1e-12, "offset": 0.0},  # allows 0 - 1 A in 250 pA - Steps
    "time": {"gain": 1e-9, "offset": 0.0},
}


def raw_to_si(
    values_raw: Union[np.ndarray, float, int], cal: dict
) -> Union[np.ndarray, float]:
    """Helper to convert between physical units and raw uint values

    :param values_raw: number or numpy array with raw values
    :param cal: calibration-dict with entries for gain and offset
    :return: converted number or array
    """
    values_si = values_raw * cal["gain"] + cal["offset"]
    values_si[values_si < 0.0] = 0.0
    return values_si


def si_to_raw(values_si: Union[np.ndarray, float], cal: dict) -> Union[np.ndarray, int]:
    """Helper to convert between physical units and raw uint values

    :param values_si: number or numpy array with values in physical units
    :param cal: calibration-dict with entries for gain and offset
    :return: converted number or array
    """
    values_raw = (values_si - cal["offset"]) / cal["gain"]
    values_raw[values_raw < 0.0] = 0.0
    return values_raw
