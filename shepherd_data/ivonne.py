import math
from typing import Union, NoReturn
import logging
import numpy as np
import pandas as pd
import pickle
import scipy  # used for interpolation
from pathlib import Path
from tqdm import tqdm, trange

from shepherd_data import Writer, logger
from shepherd_data.mppt import MPPTracker, OpenCircuitTracker, OptimalTracker


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


def get_voc(coeffs: pd.DataFrame):
    """Open-circuit voltage of IV curve with given coefficients."""
    return np.log(coeffs["a"] / coeffs["b"] + 1) / coeffs["c"]


def get_isc(coeffs: pd.DataFrame):
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

    def refresh_file_stats(self) -> NoReturn:
        self.runtime_s = round(self._df.shape[0] / self.samplerate_sps, 3)
        self.file_size = self.file_path.stat().st_size
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def convert_2_ivcurves(self,
                           shp_output: Path,
                           v_max: float = 5.0,
                           pts_per_curve: int = 1000,
                           duration_s: float = None,
                           ) -> NoReturn:
        """Transforms previously recorded IV curves to shepherd hdf database.

        Shepherd should work with IV 'surfaces', where we have an IV curve for every
        point in time. These curves will be represented as one 'prototype' curve and
        a series of two transformation coefficients that scale the prototype curve along
        the two dimensions. This function reads IV curves recorded with the IVonne tool,
        takes the first curve as prototype, calculates the corresponding transformation
        coefficients and stores them as a shepherd-compatible hdf database.


        :param shp_output: Path where the resulting hdf file shall be stored
        :param v_max: Maximum voltage supported by shepherd
        :param pts_per_curve: Number of sampling points of the prototype curve
        :param duration_s: time to stop in seconds, counted from beginning
        """
        if isinstance(duration_s, (float, int)) and self.runtime_s > duration_s:
            logger.info(f"  -> gets trimmed to {duration_s} s")
            df_input = self._df.iloc[0:int(duration_s * self.samplerate_sps)]
        else:
            df_input = self._df

        if shp_output.exists():
            logger.warning(f"[{self.dev}] {shp_output.name} already exists, will skip")
            return

        v_proto = np.linspace(0, v_max, pts_per_curve)

        df_input["timestamp"] = pd.TimedeltaIndex(data=df_input["time"], unit="s")
        df_input = df_input.set_index("timestamp")

        with Writer(shp_output, datatype="ivcurve", window_samples=pts_per_curve) as db:

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

    def convert_2_ivsamples(self,
                            shp_output: Path,
                            v_max: float = 5.0,
                            duration_s: float = None,
                            tracker: MPPTracker = None,
                            ) -> NoReturn:
        """Transforms shepherd IV curves to shepherd IV traces.

        For the 'buck' and 'buck-boost' modes, shepherd takes voltage and current traces.
        These can be recorded with shepherd or generated from existing IV curves by, for
        example, maximum power point tracking. This function takes a shepherd IV curve
        file and applies the specified MPPT algorithm to extract the corresponding
        voltage and current traces.

        TODO:
            - allow to use harvester-model in shepherd-code
            - generalize and put it into main code

        :param shp_output: Path where the resulting hdf file shall be stored
        :param v_max: Maximum voltage supported by shepherd
        :param duration_s: time to stop in seconds, counted from beginning
        :param tracker: VOC or OPT
        """
        if isinstance(duration_s, (float, int)) and self.runtime_s > duration_s:
            logger.info(f"  -> gets trimmed to {duration_s} s")
            df_input = self._df.iloc[0:int(duration_s * self.samplerate_sps)]
        else:
            df_input = self._df

        if shp_output.exists():
            logger.warning(f"[{self.dev}] {shp_output.name} already exists, will skip")
            return

        if tracker is None:
            tracker = OptimalTracker(v_max, )

        df_input["voc"] = get_voc(df_input)
        df_input.loc[df_input["voc"] >= v_max, "voc"] = v_max
        df_tracked = tracker.process(df_input)
        df_tracked["timestamp"] = pd.TimedeltaIndex(data=df_tracked["time"], unit="s")
        df_tracked = df_tracked[["time", "v", "i", "timestamp"]]

        with Writer(shp_output, datatype="ivsample") as db:

            interval_us = round(db.sample_interval_ns / 1000)
            up_factor = self.sample_interval_ns // db.sample_interval_ns
            max_elements = math.ceil(db.max_elements // up_factor)
            iterations = math.ceil(df_tracked.shape[0] / max_elements)
            job_iter = trange(0, df_tracked.shape[0], max_elements, desc=f"generating ivsamples",
                              leave=False, disable=iterations < 8)

            for idx in job_iter:
                # pandas selects (max_elements + 1) elements, so upsampling is without gaps, but we have to drop a sample at the end
                df_coeffs = df_tracked.loc[idx:idx+max_elements, :].set_index("timestamp")
                df_coeffs = df_coeffs.resample(f"{interval_us}us").interpolate(method="cubic").reset_index(drop=True).iloc[:-1]
                db.append_iv_data_si(df_coeffs["time"].to_numpy(),
                                     df_coeffs["v"].to_numpy(),
                                     df_coeffs["i"].to_numpy())

    def upsample_2_isc_voc(self,
                           shp_output: Path,
                           v_max: float = 5.0,
                           duration_s: float = None,
                           ) -> NoReturn:
        """Transforms shepherd IV curves to shepherd IV traces.

        For the 'buck' and 'buck-boost' modes, shepherd takes voltage and current traces.
        These can be recorded with shepherd or generated from existing IV curves by, for
        example, maximum power point tracking. This function takes a shepherd IV curve
        file and applies the specified MPPT algorithm to extract the corresponding
        voltage and current traces.

        TODO:
            - allow to use harvester-model in shepherd-code
            - generalize and put it into

        :param shp_output: Path where the resulting hdf file shall be stored
        :param v_max: Maximum voltage supported by shepherd
        :param duration_s: time to stop in seconds, counted from beginning
        :param tracking_algo: VOC or OPT
        """
        if isinstance(duration_s, (float, int)) and self.runtime_s > duration_s:
            logger.info(f"  -> gets trimmed to {duration_s} s")
            df_input = self._df.iloc[0:int(duration_s * self.samplerate_sps)]
        else:
            df_input = self._df
        if shp_output.exists():
            logger.warning(f"[{self.dev}] {shp_output.name} already exists, will skip")
            return

        df_input["voc"] = get_voc(df_input)  # TODO: this could be done in iter-loop
        df_input.loc[df_input["voc"] >= v_max, "voc"] = v_max
        df_input["isc"] = get_isc(df_input)
        df_input["timestamp"] = pd.TimedeltaIndex(data=df_input["time"], unit="s")
        df_input = df_input[["time", "voc", "isc", "timestamp"]]

        with Writer(shp_output, datatype="isc_voc") as db:

            interval_us = round(db.sample_interval_ns / 1000)
            up_factor = self.sample_interval_ns // db.sample_interval_ns
            max_elements = math.ceil(db.max_elements // up_factor)
            iterations = math.ceil(df_input.shape[0] / max_elements)
            job_iter = trange(0, df_input.shape[0], max_elements, desc=f"generating upsample",
                              leave=False, disable=iterations < 8)

            for idx in job_iter:
                # pandas selects (max_elements + 1) elements, so upsampling is without gaps, but we have to drop a sample at the end
                df_coeffs = df_input.loc[idx:idx+max_elements, :].set_index("timestamp")
                df_coeffs = df_coeffs.resample(f"{interval_us}us").interpolate(method="cubic").reset_index(drop=True).iloc[:-1]
                db.append_iv_data_si(df_coeffs["time"].to_numpy(),
                                     df_coeffs["voc"].to_numpy(),
                                     df_coeffs["isc"].to_numpy())
