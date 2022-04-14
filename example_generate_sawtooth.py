from pathlib import Path
import numpy as np

from datalib import ShepherdReader, ShepherdWriter

file_path = Path("./hrv_artificial_sawtooth.h5")

with ShepherdWriter(file_path, compression=None) as file:

    duration_s = 60
    repetitions = 60 * 24
    timestamp_now_s = 0

    for idx in range(repetitions):

        timestamp_next_s = int(timestamp_now_s + duration_s)
        timestamps = np.arange(timestamp_now_s, timestamp_next_s, file.sample_interval_ns / 10**9)
        timestamp_now_s = timestamp_next_s

        # values in SI units
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))

        file.append_iv_data_si(timestamps, voltages, currents)


with ShepherdReader(file_path) as db:
    print(f"Mode: {db.get_mode()}")
    print(f"Window: {db.get_window_samples()}")
    print(f"Config: {db.get_config()}")
    db.save_metadata()

