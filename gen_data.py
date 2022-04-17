import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mppt import OpenCircuitTracker
from mppt import OptimalTracker


# config for output-files
f_sample_Hz = 100_000
duration_s = 600.0

# optimize hdf5-File
chunk_shape = (10_000,)
compression_algo = "lzf"

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
    curve2trace("db_curves.h5", "db_traces.h5")
