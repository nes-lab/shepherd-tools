"""Harvesters, simple and fast approach.

Might be exchanged by shepherds py-model of pru-harvesters.
"""

import numpy as np
import pandas as pd

from shepherd_core import Calc_t


def iv_model(voltages: Calc_t, coeffs: pd.Series) -> Calc_t:
    """Calculate simple diode based model (equivalent circuit diagram) of a solar panel IV curve.

    :param voltages: Load voltage of the solar panel
    :param coeffs: three generic coefficients
    :return: Solar current at given load voltage
    """
    currents = float(coeffs["a"]) - float(coeffs["b"]) * (
        np.exp(float(coeffs["c"]) * voltages) - 1.0
    )
    if isinstance(currents, np.ndarray):
        currents[currents < 0.0] = 0.0
    else:
        currents = max(0.0, currents)

    return currents


def find_oc(v_arr: np.ndarray, i_arr: np.ndarray, ratio: float = 0.05) -> np.ndarray:
    """Approximates opencircuit voltage.

    Searches last current value that is above a certain ratio of the short-circuit
    current.
    """
    return v_arr[np.argmax(i_arr < i_arr[0] * ratio)]


class MPPTracker:
    """Prototype for a MPPT-class.

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    """

    def __init__(self, v_max: float = 5.0, pts_per_curve: int = 1000) -> None:
        self.pts_per_curve: int = pts_per_curve
        self.v_max: float = v_max
        self.v_proto: np.ndarray = np.linspace(0, v_max, pts_per_curve)

    def process(self, coeffs: pd.DataFrame) -> pd.DataFrame:
        """Apply harvesting model to input data.

        :param coeffs: ivonne coefficients
        :return: ivsample-data
        """


class OpenCircuitTracker(MPPTracker):
    """Open-circuit (-voltage) based MPPT.

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    :param ratio:  (float) Ratio of open-circuit voltage to track
    """

    def __init__(self, v_max: float = 5.0, pts_per_curve: int = 1000, ratio: float = 0.8) -> None:
        super().__init__(v_max, pts_per_curve)
        self.ratio = ratio

    def process(self, coeffs: pd.DataFrame) -> pd.DataFrame:
        """Apply harvesting model to input data.

        :param coeffs: ivonne coefficients
        :return: ivsample-data
        """
        coeffs["icurve"] = coeffs.apply(lambda x: iv_model(self.v_proto, x), axis=1)
        if "voc" not in coeffs.columns:
            coeffs["voc"] = coeffs.apply(lambda x: find_oc(self.v_proto, x["ivcurve"]), axis=1)
        coeffs["rvoc_pos"] = coeffs.apply(
            lambda x: np.argmax(self.v_proto[self.v_proto < self.ratio * x["voc"]]),
            axis=1,
        )
        coeffs["i"] = coeffs.apply(lambda x: x["icurve"][x["rvoc_pos"]], axis=1)
        coeffs["v"] = coeffs.apply(lambda x: self.v_proto[x["rvoc_pos"]], axis=1)
        return coeffs


class OptimalTracker(MPPTracker):
    """Optimal MPPT by looking at the whole curve.

    Calculates optimal harvesting voltage for every time and corresponding IV curve.

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    """

    def __init__(self, v_max: float = 5.0, pts_per_curve: int = 1000) -> None:
        super().__init__(v_max, pts_per_curve)

    def process(self, coeffs: pd.DataFrame) -> pd.DataFrame:
        """Apply harvesting model to input data.

        :param coeffs: ivonne coefficients
        :return: ivsample-data
        """
        coeffs["icurve"] = coeffs.apply(lambda x: iv_model(self.v_proto, x), axis=1)
        coeffs["pcurve"] = coeffs.apply(lambda x: self.v_proto * x["icurve"], axis=1)
        coeffs["max_pos"] = coeffs.apply(lambda x: np.argmax(x["pcurve"]), axis=1)
        coeffs["i"] = coeffs.apply(lambda x: x["icurve"][x["max_pos"]], axis=1)
        coeffs["v"] = coeffs.apply(lambda x: self.v_proto[x["max_pos"]], axis=1)
        return coeffs
