""" Prototype for exploring gains of removing time-dataset.

- harvesting datasets for the testbed don't need timebase
- generate timestamp dynamically -> sample-frequency is constant and start-TS is known
- static envs and stochastic envs with on-off voltage-levels (low entropy) are mainly
  blown up in size by the timestamps

Example Calculation:
- 20 Combinations, 20 Nodes, 4 h take 1.6 TiB ATM
- this is 3844 MiB per file and 74 MiB when omitting TS
- ~50x reduction in size is a good reason to support that feature
- even the random-walk seems to shrink by x3.5
"""
from pathlib import Path

from shepherd_core import Writer, Compression, CalibrationSeries, CalibrationPair, Reader
from shepherd_core.data_models import EnergyDType

path_demo = Path(r".\artificial_static_4h")
path_demo = Path(r"G:\# neslab-nova-data\artificial_multivariate_random_walk\solar_ANYSOLAR_KXOB201K04F_298K")

file_paths = list(path_demo.rglob("*.h5"))

for iter in [3]:
    path_inp = file_paths[iter]
    path_out = path_inp.with_stem(path_inp.stem + "_no_time")
    print(path_inp)
    print(f"Size-Inp: {path_inp.stat().st_size}")
    with Reader(path_inp, verbose=False) as reader:

        with Writer(
            file_path=path_out,
            compression=Compression.gzip1,
            mode="harvester",
            datatype=EnergyDType.ivsample,
            window_samples=0,
            cal_data=CalibrationSeries(
                # sheep can skip scaling if cal is ideal (applied here)
                voltage=CalibrationPair(gain=1e-6, offset=0),
                current=CalibrationPair(gain=1e-9, offset=0),
            ),
            verbose=False,
            ) as writer:

                writer.store_hostname(reader.get_hostname())
                size_new = reader.samples_n

                writer.ds_voltage.resize((size_new,))
                writer.ds_current.resize((size_new,))


                writer.ds_current[:size_new] = reader.ds_current[:size_new]
                writer.ds_voltage[:size_new] = reader.ds_voltage[:size_new]

    print(f"Size-Out: {path_out.stat().st_size}")

