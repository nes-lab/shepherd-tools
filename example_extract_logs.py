import os
from pathlib import Path

from datalib import ShepherdReader

# script iterates through this directory and analyzes hdf5-files
# - prints cpu-utilization and data-rate
# - saves logging-info to files

flist = os.listdir("./")
for file in flist:
    fpath = Path(file)
    if not fpath.is_file():
        continue
    if ".h5" not in fpath.suffix:
        continue

    with ShepherdReader(fpath, verbose=False) as fh:
        fh.save_metadata()
        try:
            fh.save_csv(fh["sysutil"])
            fh.save_csv(fh["timesync"])

            fh.save_log(fh["dmesg"])
            fh.save_log(fh["exceptions"])
            fh.save_log(fh["uart"])

            # also generate overall cpu-util
            ds_cpu = fh["sysutil"]["cpu"]

            print(f"{file} \t-> {fh['mode']}, "
                  f"{ds_cpu.attrs['description']} = {round(ds_cpu[:].mean(), 2)}, "
                  f"data-rate = {round(fh.data_rate / 2**10)} KiB/s, "
                  f"energy = {fh.calc_energy()}")
        except KeyError:
            continue
