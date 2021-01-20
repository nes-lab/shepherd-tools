import h5py
import numpy as np
import pickle
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

from mppt import OpenCircuitTracker
from mppt import OptimalTracker


Fs = 100_000
T = 300.0


def iv_model(v: float, coeffs: dict):
    """Simple diode based model of a solar panel IV curve.

    Args:
        v (float): Load voltage of the solar panel
        coeffs (dict): three generic coefficients

    Returns:
        Solar current at given load voltage
    """
    i = coeffs["a"] - coeffs["b"] * (np.exp(coeffs["c"] * v) - 1)
    if hasattr(i, "__len__"):
        i[i < 0] = 0
    else:
        i = max(0, i)
    return i


def get_voc(coeffs):
    """Open-circuit voltage of IV curve with given coefficients."""
    return np.log(coeffs["a"] / coeffs["b"] + 1) / coeffs["c"]


def get_isc(coeffs):
    """Short-circuit current of IV curve with given coefficients."""
    return coeffs["a"]


def load_iv_data(path: Path):
    with open(path, "rb") as f:
        df = pickle.load(f)
    return df


def gen_regvoltage(db_path: Path, v_start: float = 3.6, v_end: float = 1.9):
    """Generates an hdf database with a voltage traces.

    Shepherd has a mode where it directly supplies the target node with a given
    voltage. This function generates the corresponding voltage trace. In this
    example, the voltage linearly ramps down from v_start to v_end.

    Args:
        db_path (pathlib.Path): Path for the resulting hdf file
        v_start (float): Start voltage at the beginning of the trace
        v_end (float): End voltage at the end of the trace
    """
    with h5py.File("db_voltage.h5", "w") as db:
        db.attrs["type"] = "SHEPHERD_REGVOLTAGE"
        data_grp = db.create_group("data")

        timestamps = np.arange(0, int(T * 1e9), int(1 / Fs * 1e9))
        ds_time = data_grp.create_dataset(
            "time", (Fs * T,), data=timestamps, dtype="u8"
        )
        ds_time.attrs["unit"] = "ns"

        voltages = np.linspace(v_start * 1e6, v_end * 1e6, int(Fs * T))
        ds_voltage = data_grp.create_dataset(
            "voltage", (Fs * T,), data=voltages, dtype="u4"
        )
        ds_voltage.attrs["unit"] = "uV"


def gen_ivcurve(
    curve_recordings: Path, db_curves: Path, v_max: float = 5, pts_per_curve: int = 1024
):
    """Transforms previously recorded IV curves to shepherd hdf database.

    Shepherd should work with IV 'surfaces', where we have an IV curve for every
    point in time. These curves will be represented as one 'prototype' curve and
    a series of two transformation coefficients that scale the prototype curve along
    the two dimensions. This function reads IV curves recorded with the IVonne tool,
    takes the first curve as prototype, calculates the corresponding transformation
    coefficients and stores them as a shepherd-compatible hdf database.

    Args:
        curve_recordings (pathlib.Path): Path to IVonne measurements
        db_curves (pathlib.Path): Path where the resulting hdf file shall be stored
        v_max (float): Maximum voltage supported by shepherd
        pts_per_curve (int): Number of sampling points of the prototype curve
    """
    df_sampled = load_iv_data(curve_recordings)
    fs_iv_data = 50.0

    v_proto = np.linspace(0, v_max, pts_per_curve)
    i_proto = iv_model(v_proto, df_sampled.iloc[0])

    voc_proto = get_voc(df_sampled.iloc[0])
    isc_proto = get_isc(df_sampled.iloc[0])

    trans_coeffs = np.empty((len(df_sampled), 2))
    for i in range(len(df_sampled)):
        trans_coeffs[i, 0] = get_voc(df_sampled.iloc[i]) / voc_proto
        trans_coeffs[i, 1] = get_isc(df_sampled.iloc[i]) / isc_proto

    # Upsample transformation coefficients to 100kHz target frequency
    ts = np.arange(0, len(df_sampled) / fs_iv_data, 1 / fs_iv_data)
    t_idx = pd.TimedeltaIndex(data=ts, unit="s")

    df_coeffs = pd.DataFrame(data=trans_coeffs, index=t_idx)
    df_coeffs = df_coeffs.resample("10us").interpolate(method="cubic")
    coeffs_interp = df_coeffs.iloc[:, :].values

    with h5py.File(db_curves, "w") as db:
        db.attrs["type"] = "SHEPHERD_IVCURVE"

        proto_grp = db.create_group("proto_curve")
        ds_proto_voltage = proto_grp.create_dataset(
            "voltage", (1024,), data=v_proto * 1e6, dtype="u4"
        )
        ds_proto_voltage.attrs["unit"] = "uV"

        ds_proto_current = proto_grp.create_dataset(
            "current", (1024,), data=i_proto * 1e9, dtype="u4"
        )
        ds_proto_current.attrs["unit"] = "nA"

        data_grp = db.create_group("data")

        ds_time = data_grp.create_dataset("time", (len(df_coeffs),), dtype="u8")
        ds_time.attrs["unit"] = f"ns"
        ds_time[:] = np.arange(0, 1 / Fs * len(df_coeffs) * 1e9, int(1 / Fs * 1e9))

        ds_trans_coeffs = data_grp.create_dataset(
            "trans_coeffs",
            coeffs_interp.shape,
            data=(coeffs_interp - 1.0) * (2 ** 24),
            dtype="i4",
        )
        ds_trans_coeffs.attrs["unit"] = "2^24"


def curve2trace(
    curve_db: Path, trace_db: Path, tracking_algorithm: str = "OpenCircuit"
):
    """Transforms shepherd IV curves to shepherd IV traces.

    For the 'buck' and 'buck-boost' modes, shepherd takes voltage and current traces.
    These can be recorded with shepherd or generated from existing IV curves by, for
    example, maximum power point tracking. This function takes a shepherd IV curve
    file and applies the specified MPPT algorithm to extract the corresponding
    voltage and current traces.

    Args:
        curve_db (pathlib.Path): Path to shepherd IV curve hdf database
        trace_db (pathlib.Path): Path where the resulting hdf file shall be stored
        tracking_algorithm (str): MPPT algorithm to apply to the curves
    """
    with h5py.File(curve_db, "r") as db_in:
        v_proto = db_in["proto_curve"]["voltage"][:]
        i_proto = db_in["proto_curve"]["current"][:]

        trans_coeffs = db_in["data"]["trans_coeffs"][:].astype(float) / (2 ** 24) + 1.0

        tracker_class = globals()[f"{tracking_algorithm}Tracker"]
        mpp_tracker = tracker_class(v_proto, i_proto)

        v_hrvst = np.empty((trans_coeffs.shape[0],))
        i_hrvst = np.empty_like(v_hrvst)

        for i in range(trans_coeffs.shape[0]):
            v_hrvst[i], i_hrvst[i] = mpp_tracker.process(trans_coeffs[i, :])
            if not i % 100000:
                print(f"{i/trans_coeffs.shape[0]*100:.2f}%")

        with h5py.File(trace_db, "w") as db_out:
            db_out.attrs["type"] = "SHEPHERD_IVTRACE"
            data_grp = db_out.create_group("data")
            ds_time = data_grp.create_dataset(
                "time", (trans_coeffs.shape[0],), dtype="u8"
            )
            data_grp["time"].attrs["unit"] = "ns"
            ds_time[:] = db_in["data"]["time"][:]

            ds_voltage = data_grp.create_dataset(
                "voltage", (len(v_hrvst),), data=v_hrvst, dtype="u4"
            )
            ds_voltage.attrs["unit"] = "uV"

            ds_current = data_grp.create_dataset(
                "current", (len(i_hrvst),), data=i_hrvst, dtype="u4"
            )
            ds_current.attrs["unit"] = "nA"


if __name__ == "__main__":
    gen_regvoltage("db_voltage.h5")
    gen_ivcurve("jogging_10m.iv", "db_curves.h5")
    curve2trace("db_curves.h5", "db_traces.h5")
