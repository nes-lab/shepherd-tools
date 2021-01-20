import numpy as np
from scipy import interpolate
from scipy.optimize import minimize_scalar

import matplotlib.pyplot as plt


def find_oc(v_arr, i_arr, ratio: float = 0.05):
    """Approximates opencircuit voltage.

    Searches last current value that is above a certain ratio of the short-circuit
    current.
    """

    return v_arr[np.argmax(i_arr < i_arr[0] * ratio)]


class MPPTracker(object):
    def __init__(
        self, v_proto: np.array, i_proto: np.array, f_sampling: float = 100000.0
    ):
        self.time = 0.0
        self.f_sampling = f_sampling
        self.T_sampling = 1.0 / f_sampling
        self.fn_proto = interpolate.interp1d(
            v_proto, i_proto, bounds_error=False, fill_value="extrapolate"
        )

    def tick(self):
        self.time += self.T_sampling


class OpenCircuitTracker(MPPTracker):
    """Open-circuit based MPPT

    Periodically samples the open-circuit voltage and regulates the harvesting voltage
    to a given ratio of the open-circuit voltage for the remaining period.

    Args:
        v_proto (np.array): Voltage values of prototype IV curve
        i_proto (np.array): Corresponding current values of prototype IV curve
        ratio (float): Ratio of open-circuit voltage to track
        period (float): Open-circuit sampling period in seconds
        t_probing (float): Duration of open-circuit sampling in seconds
        f_sampling (float): Data sampling frequency
    """

    def __init__(
        self,
        v_proto: np.array,
        i_proto: np.array,
        ratio: float = 0.8,
        period: float = 16,
        t_probing: float = 0.256,
        f_sampling: float = 100000.0,
    ):
        super().__init__(v_proto, i_proto, f_sampling)
        self.ratio = ratio
        self.period = period
        self.t_probing = t_probing
        self.probing_countdown = 0.0
        self.voc_proto = find_oc(v_proto, i_proto)

        self.counter = 0

    def process(self, trans_coeffs: np.array):

        # Sampling period starts
        if not int(self.time * self.f_sampling) % int(self.period * self.f_sampling):
            self.probing_countdown = self.t_probing

        # While OC sampling is running
        if self.probing_countdown > 0:
            self.probing_countdown -= self.T_sampling
            if self.probing_countdown <= 0:
                self.v_hrvst = self.ratio * self.voc_proto * trans_coeffs[0]
            else:
                self.v_hrvst = self.voc_proto * trans_coeffs[0]
            i_hrvst = 0.0
        else:
            i_hrvst = self.fn_proto(self.v_hrvst / trans_coeffs[0]) * trans_coeffs[1]

        super().tick()
        return self.v_hrvst, i_hrvst


class OptimalTracker(MPPTracker):
    """Optimal MPPT

    Calculates optimal harvesting voltage for every time and corresponding IV curve.
    Due to the multiplicative scaling approach, it's enough to optimize for the
    prototype curve once and then scale that solution according to the current
    transformation coefficients.

    Args:
        v_proto (np.array): Voltage values of prototype IV curve
        i_proto (np.array): Corresponding current values of prototype IV curve
        f_sampling (float): Data sampling frequency
    """

    def __init__(
        self,
        v_proto: np.array,
        i_proto: np.array,
        f_sampling: float = 100000.0,
    ):
        super().__init__(v_proto, i_proto, f_sampling)
        voc_proto = find_oc(v_proto, i_proto)
        res = minimize_scalar(
            self.obj_fun,
            bounds=(0, voc_proto),
            method="bounded",
        )
        self.v_opt_proto = res.x

    def obj_fun(self, v):
        pwr = -v * self.fn_proto(v)
        return pwr

    def process(self, trans_coeffs):
        v_opt = self.v_opt_proto * trans_coeffs[0]
        i_hrvst = self.fn_proto(self.v_opt_proto) * trans_coeffs[1]
        super().tick()
        return v_opt, i_hrvst
