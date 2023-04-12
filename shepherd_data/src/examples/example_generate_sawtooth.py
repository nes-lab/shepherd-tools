"""
script will:
- generate a repetitive ramp / sawtooth
- save file-metadata to yaml
- read file and query some data
"""
from pathlib import Path

import numpy as np
from tqdm import trange

import shepherd_data as shpd

if __name__ == "__main__":
    file_path = Path("./hrv_sawtooth_1h.h5")

    with shpd.Writer(file_path, compression=1) as file:
        file.set_hostname("artificial")
        duration_s = 60
        repetitions = 60
        timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)

        # values in SI units
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))

        for idx in trange(repetitions, desc="generate"):
            timestamps = idx * duration_s + timestamp_vector
            file.append_iv_data_si(timestamps, voltages, currents)

        file.save_metadata()

    with shpd.Reader(file_path) as db:
        print(f"Mode:     {db.get_mode()}")
        print(f"Datatype: {db.get_datatype()}")
        print(f"Window:   {db.get_window_samples()} samples")
        print(f"Config:   {db.get_config()}")
        print(f"Structure: \n\n{db}")
