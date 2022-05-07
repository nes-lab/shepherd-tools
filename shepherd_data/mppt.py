import numpy as np
import pandas as pd


def iv_model(v: np.ndarray, coeffs: pd.DataFrame):
    """Simple diode based model of a solar panel IV curve.

    Args:
        :param v: Load voltage of the solar panel
        :param coeffs: three generic coefficients

    Returns:
        Solar current at given load voltage
    """
    i = coeffs["a"] - coeffs["b"] * (np.exp(coeffs["c"] * v) - 1)
    if hasattr(i, "__len__"):
        i[i < 0] = 0
    else:
        i = max(0, i)
    return i


def find_oc(v_arr, i_arr, ratio: float = 0.05):
    """Approximates opencircuit voltage.

    Searches last current value that is above a certain ratio of the short-circuit
    current.
    """
    return v_arr[np.argmax(i_arr < i_arr[0] * ratio)]


class MPPTracker:
    """Prototype

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    """

    def __init__(self, v_max: float = 5.0, pts_per_curve: int = 1000):
        self.pts_per_curve = pts_per_curve
        self.v_max = v_max
        self.v_proto = np.linspace(0, v_max, pts_per_curve)

    def process(self, coeffs: pd.DataFrame) -> pd.DataFrame:
        pass


class OpenCircuitTracker(MPPTracker):
    """Open-circuit based MPPT

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    :param ratio:  (float) Ratio of open-circuit voltage to track
    """

    def __init__(
        self, v_max: float = 5.0, pts_per_curve: int = 1000, ratio: float = 0.8
    ):
        super().__init__(v_max, pts_per_curve)
        self.ratio = ratio

    def process(self, coeffs: pd.DataFrame) -> pd.DataFrame:
        coeffs["icurve"] = coeffs.apply(lambda x: iv_model(self.v_proto, x), axis=1)
        if "voc" not in coeffs.columns:
            coeffs["voc"] = coeffs.apply(
                lambda x: find_oc(self.v_proto, x["ivcurve"]), axis=1
            )
        coeffs["rvoc_pos"] = coeffs.apply(
            lambda x: np.argmax(self.v_proto[self.v_proto < self.ratio * x["voc"]]),
            axis=1,
        )
        coeffs["i"] = coeffs.apply(lambda x: x["icurve"][x["rvoc_pos"]], axis=1)
        coeffs["v"] = coeffs.apply(lambda x: self.v_proto[x["rvoc_pos"]], axis=1)
        return coeffs


class OptimalTracker(MPPTracker):
    """Optimal MPPT

    Calculates optimal harvesting voltage for every time and corresponding IV curve.

    :param v_max: Maximum voltage supported by shepherd
    :param pts_per_curve: resolution of internal ivcurve
    """

    def __init__(self, v_max: float = 5.0, pts_per_curve: int = 1000):
        super().__init__(v_max, pts_per_curve)

    def process(self, coeffs: pd.DataFrame):
        coeffs["icurve"] = coeffs.apply(lambda x: iv_model(self.v_proto, x), axis=1)
        coeffs["pcurve"] = coeffs.apply(lambda x: self.v_proto * x["icurve"], axis=1)
        coeffs["max_pos"] = coeffs.apply(lambda x: np.argmax(x["pcurve"]), axis=1)
        coeffs["i"] = coeffs.apply(lambda x: x["icurve"][x["max_pos"]], axis=1)
        coeffs["v"] = coeffs.apply(lambda x: self.v_proto[x["max_pos"]], axis=1)
        return coeffs
