import h5py
import numpy as np
import pickle
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

from mppt import OpenCircuitTracker
from mppt import OptimalTracker


# config for output-files
f_sample_Hz = 100_000
duration_s = 30.0

# optimize hdf5-File
chunk_shape = (10_000,)
compression_algo = "lzf"

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

        timestamps = np.arange(0, int(duration_s * 1e9), int(1 / f_sample_Hz * 1e9))
        ds_time = data_grp.create_dataset(
            "time", (f_sample_Hz * duration_s,), data=timestamps, dtype="u8",
            chunks=chunk_shape, compression=compression_algo,
        )
        ds_time.attrs["unit"] = "ns"
        ds_time.attrs["description"] = "system time [ns]"

        voltages = np.linspace(v_start * 1e6, v_end * 1e6, int(f_sample_Hz * duration_s))
        ds_voltage = data_grp.create_dataset(
            "voltage", (f_sample_Hz * duration_s,), data=voltages, dtype="u4",
            chunks=chunk_shape, compression=compression_algo,
        )
        ds_voltage.attrs["unit"] = "V"
        ds_voltage.attrs["description"] = "voltage [V] = value * gain + offset"
        ds_voltage.attrs["gain"] = 1e-6
        ds_voltage.attrs["offset"] = 0.0

        currents = np.linspace(100, 2000, int(f_sample_Hz * duration_s))
        ds_current = data_grp.create_dataset(
            "current", (f_sample_Hz * duration_s,), data=currents, dtype="u4",
            chunks=chunk_shape, compression=compression_algo,
        )
        ds_current.attrs["unit"] = "A"
        ds_current.attrs["description"] = "current [A] = value * gain + offset"
        ds_current.attrs["gain"] = 1e-6
        ds_current.attrs["offset"] = 0.0



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
    print(f"Length of IV-Curve is {len(df_sampled) / fs_iv_data} s [{curve_recordings}]")
    if len(df_sampled) / fs_iv_data > duration_s:
        print(f"  -> gets trimmed to {duration_s} s")
        df_sampled = df_sampled.iloc[0:int(duration_s * fs_iv_data)]

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
            "voltage", (1024,), data=v_proto * 1e6, dtype="u4",
            chunks=True, compression=compression_algo,
        )
        ds_proto_voltage.attrs["unit"] = "V"
        ds_proto_voltage.attrs["description"] = "voltage [V] = value * gain + offset"
        ds_proto_voltage.attrs["gain"] = 1e-6
        ds_proto_voltage.attrs["offset"] = 0

        ds_proto_current = proto_grp.create_dataset(
            "current", (1024,), data=i_proto * 1e9, dtype="u4",
            chunks=True, compression=compression_algo,
        )
        ds_proto_current.attrs["unit"] = "A"
        ds_proto_current.attrs["description"] = "current [A] = value * gain + offset"
        ds_proto_current.attrs["gain"] = 1e-9
        ds_proto_current.attrs["offset"] = 0

        data_grp = db.create_group("data")

        ds_time = data_grp.create_dataset(
            "time", (len(df_coeffs),), dtype="u8",
            chunks=chunk_shape, compression=compression_algo,
            )
        ds_time.attrs["unit"] = f"ns"
        ds_time.attrs["description"] = "system time [ns]"
        ds_time[:] = np.arange(0, len(df_coeffs) * 10 ** 9 / f_sample_Hz, int(10 ** 9 // f_sample_Hz))

        ds_trans_coeffs = data_grp.create_dataset(
            "trans_coeffs",
            coeffs_interp.shape,
            data=(coeffs_interp - 1.0) * (2 ** 24),
            dtype="i4",
            chunks=(chunk_shape[0], coeffs_interp.shape[1]),
            compression=compression_algo,
        )
        ds_trans_coeffs.attrs["unit"] = "n"
        ds_trans_coeffs.attrs["description"] = "coeff [n] = value * gain + offset"
        ds_trans_coeffs.attrs["gain"] = 2**-24
        ds_trans_coeffs.attrs["offset"] = 1.0


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

        gain = db_in["data"]["trans_coeffs"].attrs["gain"]
        offset = db_in["data"]["trans_coeffs"].attrs["offset"]
        trans_coeffs = db_in["data"]["trans_coeffs"][:].astype(float) * gain + offset

        tracker_class = globals()[f"{tracking_algorithm}Tracker"]
        mpp_tracker = tracker_class(v_proto, i_proto)  # TODO: trackers don't know about gain/offset yet

        v_hrvst = np.empty((trans_coeffs.shape[0],))
        i_hrvst = np.empty_like(v_hrvst)

        for i in range(trans_coeffs.shape[0]):
            # TODO: possibly best to convert tracker into lambda and apply it to series
            v_hrvst[i], i_hrvst[i] = mpp_tracker.process(trans_coeffs[i, :])
            if not i % 100000:
                print(f"{i/trans_coeffs.shape[0]*100:.2f}%")

        with h5py.File(trace_db, "w") as db_out:
            db_out.attrs["type"] = "SHEPHERD_IVTRACE"
            data_grp = db_out.create_group("data")
            ds_time = data_grp.create_dataset(
                "time", (trans_coeffs.shape[0],), dtype="u8",
                chunks=chunk_shape, compression=compression_algo,
            )
            data_grp["time"].attrs["unit"] = "ns"
            data_grp["time"].attrs["description"] = "system time [ns]"
            ds_time[:] = db_in["data"]["time"][:]

            ds_voltage = data_grp.create_dataset(
                "voltage", (len(v_hrvst),), data=v_hrvst, dtype="u4",
                chunks=chunk_shape, compression=compression_algo,
            )
            ds_voltage.attrs["unit"] = "V"
            ds_voltage.attrs["description"] = "voltage [V] = value * gain + offset"
            ds_voltage.attrs["gain"] = 1e-6
            ds_voltage.attrs["offset"] = 0

            ds_current = data_grp.create_dataset(
                "current", (len(i_hrvst),), data=i_hrvst, dtype="u4",
                chunks=chunk_shape, compression=compression_algo,
            )
            ds_current.attrs["unit"] = "A"
            ds_current.attrs["description"] = "current [A] = value * gain + offset"
            ds_current.attrs["gain"] = 1e-9
            ds_current.attrs["offset"] = 0


if __name__ == "__main__":
    gen_regvoltage("db_voltage.h5")
    gen_ivcurve("jogging_10m.iv", "db_curves.h5")
    curve2trace("db_curves.h5", "db_traces.h5")
