from typing import Union
import logging
import numpy as np
import pandas as pd
import pickle
import scipy  # used for interpolation
from pathlib import Path
from tqdm import tqdm

from shepherd_data import Writer, logger


def iv_model(v: np.ndarray, coeffs: pd.Series):
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


def get_voc(coeffs: pd.Series):
    """Open-circuit voltage of IV curve with given coefficients."""
    return np.log(coeffs["a"] / coeffs["b"] + 1) / coeffs["c"]


def get_isc(coeffs: pd.Series):
    """Short-circuit current of IV curve with given coefficients."""
    return coeffs["a"]


class Reader(object):
    """

    """

    samplerate_sps: int = 50
    sample_interval_ns = int(10 ** 9 // samplerate_sps)
    sample_interval_s: float = (1 / samplerate_sps)

    dev = "IVonneReader"

    def __init__(self, file_path: Path, samplerate_sps: int = None, verbose: bool = True):

        logger.setLevel(logging.INFO if verbose else logging.WARNING)
        self.file_path = Path(file_path)
        if samplerate_sps is not None:
            self.samplerate_sps = samplerate_sps
        self.runtime_s = None
        self.file_size = None
        self.data_rate = None

    def __enter__(self):
        with open(self.file_path, "rb") as f:
            self._df = pickle.load(f)
        self.refresh_file_stats()
        logger.info(
            f"[{self.dev}] Reading data from '{self.file_path}'\n"
            f"\t- runtime = {self.runtime_s} s\n"
            f"\t- size = {round(self.file_size / 2 ** 10, 3)} KiB\n"
            f"\t- rate = {round(self.data_rate / 2 ** 10, 3)} KiB/s")
        return self

    def __exit__(self, *exc):
        pass

    def refresh_file_stats(self):
        self.runtime_s = round(self._df.shape[0] / self.samplerate_sps, 3)
        self.file_size = self.file_path.stat().st_size
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def convert_2_ivcurves(self,
                           shp_output: Path,
                           v_max: float = 5.0,
                           pts_per_curve: int = 1000,
                           duration_s: float = None,
                           ):
        """Transforms previously recorded IV curves to shepherd hdf database.

        Shepherd should work with IV 'surfaces', where we have an IV curve for every
        point in time. These curves will be represented as one 'prototype' curve and
        a series of two transformation coefficients that scale the prototype curve along
        the two dimensions. This function reads IV curves recorded with the IVonne tool,
        takes the first curve as prototype, calculates the corresponding transformation
        coefficients and stores them as a shepherd-compatible hdf database.

        Args:
            :param shp_output: Path where the resulting hdf file shall be stored
            :param v_max: Maximum voltage supported by shepherd
            :param pts_per_curve: Number of sampling points of the prototype curve
            :param duration_s:
        """
        if isinstance(duration_s, (float, int)) and self.runtime_s > duration_s:
            print(f"  -> gets trimmed to {duration_s} s")
            df_input = self._df.iloc[0:int(duration_s * self.samplerate_sps)]
        else:
            df_input = self._df

        v_proto = np.linspace(0, v_max, pts_per_curve)

        df_input["timestamp"] = pd.TimedeltaIndex(data=df_input["time"], unit="s")
        df_input = df_input.set_index("timestamp")

        with Writer(shp_output, datatype="ivcurve") as db:

            db.set_window_samples(pts_per_curve)

            curve_interval_us = round(db.sample_interval_ns * pts_per_curve / 1000)
            # warning: .interpolate does crash in debug-mode with typeError
            df_coeffs = df_input.resample(f"{curve_interval_us}us").interpolate(method="cubic")

            for idx, coeffs in tqdm(df_coeffs.iterrows(), desc="generating ivcurves", total=df_coeffs.shape[0]):
                i_proto = iv_model(v_proto, coeffs)
                db.append_iv_data_si(coeffs["time"], v_proto, i_proto)
                # TODO: this could be a lot faster:
                #   - use lambdas to generate i_proto
                #   - convert i_proto with lambdas to raw-values
                #   - convert v_proto to raw
                #   - replace append_ fn with custom code here, by:
                #   - final size of h5-arrays is already known, this speeds up the code!
                #   - time can be generated and set as a whole
                #   - v_proto is repetitive, can also be set as a whole
