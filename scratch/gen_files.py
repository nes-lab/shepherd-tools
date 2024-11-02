"""
Test how to effectively create a single file of a testbed-experiment

vary hdf5-files
- content: constant set, rising, random
    - rising is typical for timestamp-dataset
    - constant is typical for regulated voltage-output during emulation
- compression: none, gzip, lzf
- duplication: inner, outer
- outer compression of files

Results in MB:

            10in1   1in10

const gzip  .7      .7      -> zip both to 40 kB,  7z to 13 kB
const lzf   3       3       -> zip both to 63 kB,  7z to 22 kB
const none  229     229     -> zip both to 355 kB, 7z to 68 kB

risin gzip  75      76      -> zip both to 10 MB,  7z to 1559 kB
risin lzf   226     227     -> zip both to 7 MB,   7z to 522 kB
risin none  229     229     -> zip both to 79 MB,  7z to 6 MB,

randm none  229     229
randm gzip  229     229
randm lzf   229     229

"""
from pathlib import Path

import h5py
import numpy as np

duration_s = 60
samplerate_sps = 100_000
sample_interval_ns = round(10**9 // samplerate_sps)
contents: dict = {
        "rising": np.arange(0.0, duration_s * 1e6, sample_interval_ns / 1e3),  # usec
        "constant": np.linspace(3 * 10**6, 3 * 10**6, int(samplerate_sps * duration_s)),
        "random": np.random.default_rng().integers(0, 2**32 -1, int(samplerate_sps * duration_s)),
    }
compressions: dict = {
    "none": None,
    "gzip": "gzip",
    "lzf": "lzf",
}
duplication: int = 10
path_here = Path(__file__).parent

for content_name, content in contents.items():
    for compression_name, compression in compressions.items():

        # inner duplication
        file_path = path_here / f"{content_name}_{compression_name}_{duplication}in1.h5"
        print(f"Generating {file_path}")
        h5file = h5py.File(file_path, "w")
        grp_data = h5file.create_group("data")

        for iter in range(duplication):
            ds_name = f"current{iter}"
            grp_data.create_dataset(
                ds_name,
                shape=(0,),
                dtype="u4",
                maxshape=(None,),
                chunks=(10_000,),
                compression=compression,
            )
            grp_data[ds_name].attrs["unit"] = "A"
            grp_data[ds_name].attrs["description"] = "current [A] = value * gain + offset"
            grp_data[ds_name].resize((content.shape[0],))
            grp_data[ds_name][:] = content[:]
        h5file.close()

        # outer duplication
        ds_name = f"current"
        for iter in range(duplication):
            file_path = path_here / f"{content_name}_{compression_name}_entity{iter}.h5"
            print(f"Generating {file_path}")
            h5file = h5py.File(file_path, "w")
            grp_data = h5file.create_group("data")
            grp_data.create_dataset(
                ds_name,
                shape=(0,),
                dtype="u4",
                maxshape=(None,),
                chunks=(10_000,),
                compression=compression,
            )
            grp_data[ds_name].attrs["unit"] = "A"
            grp_data[ds_name].attrs["description"] = "current [A] = value * gain + offset"
            grp_data[ds_name].resize((content.shape[0],))
            grp_data[ds_name][:] = content[:]
            h5file.close()
