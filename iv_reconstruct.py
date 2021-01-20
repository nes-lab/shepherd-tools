import numpy as np
import matplotlib.pyplot as plt
from typing import Union
from typing import Tuple


def proto_curve(
    voltage: Union[np.array, float],
    v_open_circut: float = 2.0,
    i_short_circuit: float = 10e-3,
):
    """Represents the prototype IV curve, that serves as blueprint for all transformed curves."""
    y = -(i_short_circuit / v_open_circut) * voltage + i_short_circuit
    if hasattr(voltage, "__len__"):
        y[y < 0.0] = 0.0
    else:
        if y < 0:
            return 0
    return y


def trans_curve(
    voltage: Union[np.array, float],
    trans_coeffs: Tuple[float, float] = (1.0, 1.0),
):
    """Evaluates the transformed prototype curve at given voltage."""
    return proto_curve(voltage / trans_coeffs[0]) * trans_coeffs[1]


def find_voc_simple(fn_curve):
    """Quick search for open circuit voltage."""
    vv = np.linspace(0, 5, int(1e5))
    yy = fn_curve(vv)
    return vv[np.argmin(yy)]


def lut_interp(x: float, x_lut: np.array, y_lut: np.array):
    """Linearly interpolates values from a lookup table

    Args:
        x (int): Requested value to lookup
        x_lut (np.array): x values of lookup table entries
        y_lut (np.array): y values of lookup table entries

    Returns:
        Interpolated y value
    """
    # Find the two closest x values in the lookup table
    closest = np.argsort(np.abs(x - x_lut))[:2]
    # The order of points matters for np.interp
    if x_lut[closest[0]] < x:
        return np.interp(x, x_lut[closest], y_lut[closest])
    else:
        return np.interp(x, x_lut[closest[::-1]], y_lut[closest[::-1]])


class IVCurve(object):
    def __init__(self, proto_fn, n_pts: int = 256):
        self.proto_fn = proto_fn
        self.lut = self.make_lut(n_pts)

    def make_lut(self, n_pts: int):
        """Generates the lookup table with specified number of points."""
        self.v_lut = np.linspace(0, find_voc_simple(self.proto_fn), n_pts)
        return self.proto_fn(self.v_lut)

    def sample(
        self,
        voltage: Union[np.array, float],
        trans_coeffs: Tuple[float, float] = (1.0, 1.0),
    ):
        """Samples the transformed prototype curve with the help of the lookup table.

        This should run on the PRU with every sample. We allow to pass multiple voltages
        here for convenient evaluation.

        Args:
            voltage (int or np.array): Capacitor voltage
            trans_coeffs (tuple): User-provided transformation coefficients

        Returns:
            Harvesting current according to transformed IV curve and sampled capacitor
            voltage
        """

        # First step is to inverse transform the sampled capacitor voltage
        v_trans = voltage / trans_coeffs[0]
        if hasattr(voltage, "__len__"):
            i_trans = np.empty_like(v_trans)
            for i in range(len(v_trans)):
                i_trans[i] = lut_interp(v_trans[i], self.v_lut, self.lut)

            # Current = 0, when voltage above open circuit
            i_trans[v_trans > self.v_lut[-1]] = 0
        else:
            # Current = 0, when voltage above open circuit
            if v_trans > self.v_lut[-1]:
                return 0
            i_trans = lut_interp(v_trans, self.v_lut, self.lut)
        # Finally, project current to transformed curve
        return i_trans * trans_coeffs[1]


iv_curve = IVCurve(proto_curve)
# We assume maximum voltage of 5V
vv = np.linspace(0, 5, 100)

plt.plot(vv, trans_curve(vv, (1.0, 1.0)), label="Base curve")
plt.plot(vv, trans_curve(vv, (2.0, 4.0)), label="Transformed curve")

plt.plot(
    vv,
    iv_curve.sample(vv, (2.0, 4.0)),
    label="LUT sampled curve",
    linestyle="None",
    marker="o",
)
plt.legend()
plt.show()