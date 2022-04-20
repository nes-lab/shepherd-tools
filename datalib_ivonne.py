from typing import Union

import numpy as np
import pandas as pd
import pickle
import scipy  # used for interpolation
from pathlib import Path
from tqdm import tqdm

from datalib import ShepherdWriter


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


def load_iv_data(path: Path) -> pd.DataFrame:
    with open(path, "rb") as f:
        df = pickle.load(f)
    return df


def convert_ivonne_2_ivcurves(recording: Path,
                              shp_output: Path,
                              v_max: float = 5.0,
                              pts_per_curve: int = 1000,
                              fs_iv_data: float = 50.0,
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
        :param recording: Path to IVonne measurements
        :param shp_output: Path where the resulting hdf file shall be stored
        :param v_max: Maximum voltage supported by shepherd
        :param pts_per_curve: Number of sampling points of the prototype curve
        :param duration_s:
        :param fs_iv_data:
    """
    df_sampled = load_iv_data(recording)
    runtime_s = len(df_sampled) / fs_iv_data
    print(f"Length of IV-Curve is {runtime_s} s [{recording}]")
    if isinstance(duration_s, (float, int)) and runtime_s > duration_s:
        print(f"  -> gets trimmed to {duration_s} s")
        df_sampled = df_sampled.iloc[0:int(duration_s * fs_iv_data)]

    v_proto = np.linspace(0, v_max, pts_per_curve)

    df_sampled["timestamp"] = pd.TimedeltaIndex(data=df_sampled["time"], unit="s")
    df_sampled = df_sampled.set_index("timestamp")

    curve_interval_us = round(ShepherdWriter.sample_interval_ns * pts_per_curve / 1000)
    # warning: .interpolate does crash in debug-mode with typeError
    df_coeffs = df_sampled.resample(f"{curve_interval_us}us").interpolate(method="cubic")

    with ShepherdWriter(shp_output) as db:

        db.set_window_samples(pts_per_curve)

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
