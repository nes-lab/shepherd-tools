import os
from pathlib import Path

from datalib import ShepherdReader

# script iterates through this directory and prints cpu-utilization and data-rate
# TODO: extract all sys-util and put in csv

flist = os.listdir("./")
for file in flist:
    fpath = Path(file)
    if not fpath.is_file():
        continue
    if ".h5" not in fpath.suffix:
        continue

    with ShepherdReader(fpath, verbose=False) as fh:
        try:
            ds_cpu = fh["sysutil"]["cpu"]
            fsize = fpath.stat().st_size
            runtime_s = fh["data"]['time'].shape[0] / fh.samplerate_sps
            print(f"{file} \t-> {fh['mode']}, "
                  f"{ds_cpu.attrs['description']} = {round(ds_cpu[:].mean(), 2)}, "
                  f"data-rate = {round(fsize / runtime_s / 1024, 0)} KiB/s")
        except KeyError:
            continue
