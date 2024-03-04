"""script iterates through this directory and analyzes hdf5-files
- prints cpu-utilization and data-rate
- saves logging-info to files
- saves metadata to datasets and the file itself to yaml

CLI-Version of this is:
shepherd-data extract-meta file_or_dir
"""

import os
from pathlib import Path

import shepherd_data as shp

if __name__ == "__main__":
    flist = os.listdir("./")
    for file in flist:
        fpath = Path(file)
        if not fpath.is_file() or fpath.suffix != ".h5":
            continue

        with shp.Reader(fpath, verbose=False) as fh:
            fh.save_metadata()

            if "sysutil" in fh.h5file:
                fh.save_csv(fh["sysutil"])

                # also generate overall cpu-util
                ds_cpu = fh["sysutil"]["cpu"]

                print(
                    f"{file} \t-> {fh['mode']}, "
                    f"{ds_cpu.attrs['description']} = {round(ds_cpu[:].mean(), 2)}, "
                    f"data-rate = {round(fh.data_rate / 2**10)} KiB/s"
                )
            else:
                print(f"{file} \t-> {fh['mode']}, data-rate = {round(fh.data_rate / 2**10)} KiB/s")

            if "timesync" in fh.h5file:
                fh.save_csv(fh["timesync"])

            if "dmesg" in fh.h5file:
                fh.save_log(fh["dmesg"])
            if "exceptions" in fh.h5file:
                fh.save_log(fh["exceptions"])
            if "uart" in fh.h5file:
                fh.save_log(fh["uart"])
