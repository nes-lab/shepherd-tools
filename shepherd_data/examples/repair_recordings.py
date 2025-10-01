"""Repair & migrate older / broken shepherd recordings.

This script will:
- iterate through this directory,
- try to find and fix errors in hdf5-files / shepherd-recordings &
- old recordings from shepherd 1.x can be made available for v2.x.

-> the usage of __enter__() and __exit__() is not encouraged,
   but makes the codes simpler for this edge-case (reading- and writing-handler for same file)
"""

from pathlib import Path

from shepherd_core.data_models import EnergyDType

import shepherd_data as shp

if __name__ == "__main__":
    path_here = Path(__file__).parent
    for file in path_here.glob("*.h5"):  # for py>=3.12: case_sensitive=False
        if not file.is_file():
            continue
        print(f"Analyzing '{file.name}' ...")
        fh = shp.Reader(file, verbose=False)
        elements = fh.get_metadata(minimal=True)

        # hard criteria to detect shepherd-recording (and sort out other hdf5-files)
        if "data" not in elements:
            continue
        for dset in ["time", "current", "voltage"]:
            if dset not in elements["data"]:
                continue

        # TODO: add missing calibration or retrieve older version

        # datasets with unequal size
        ds_volt_size = fh.h5file["data"]["voltage"].shape[0]
        for dset in ["current", "time"]:
            ds_size = fh.h5file["data"][dset].shape[0]
            if ds_volt_size != ds_size:
                size_new = (min(ds_volt_size, ds_size),)
                print(" -> will bring datasets to equal size")
                fh.__exit__()
                with shp.Writer(file, modify_existing=True) as fw:
                    fw.h5file["data"]["voltage"].resize(size_new)
                    fw.h5file["data"][dset].resize(size_new)
                fh = shp.Reader(file, verbose=False)  # reopen file

        # unaligned datasets
        remaining_size = fh.h5file["data"]["voltage"].shape[0] % shp.Reader.CHUNK_SAMPLES_N
        if remaining_size != 0:
            print(" -> will align datasets")
            fh.__exit__()
            with shp.Writer(file, modify_existing=True) as fw:
                pass
            fh = shp.Reader(file, verbose=False)

        # invalid modes
        mode = fh.get_mode()
        if mode not in shp.Reader.MODE_TO_DTYPE:
            mode = shp.Writer.MODE_DEFAULT
            if "har" in fh.get_mode():  # can be harvest, harvesting, ...
                mode = "harvester"
            elif "emu" in fh.get_mode():  # can be emulation, emulate
                mode = "emulator"
            print(f" -> will set mode = {mode}")
            fh.__exit__()
            with shp.Writer(file, mode=mode, modify_existing=True) as fw:
                pass
            fh = shp.Reader(file, verbose=False)  # reopen file

        # invalid datatype
        datatype = fh.get_datatype()
        if datatype not in shp.Reader.MODE_TO_DTYPE[mode]:
            datatype = shp.Writer.DATATYPE_DEFAULT
            if "curv" in str(fh.get_datatype()):
                datatype = EnergyDType.ivcurve
            print(f" -> will set datatype = {datatype}")
            fh.__exit__()
            with shp.Writer(file, datatype=datatype, modify_existing=True) as fw:
                pass
            fh = shp.Reader(file, verbose=False)  # reopen file

        # missing window_samples
        if "window_samples" not in fh.h5file["data"].attrs:
            if datatype == EnergyDType.ivcurve:
                print("Window size missing, but ivsurface detected -> no repair")
                continue
            print(" -> will set window size = 0")
            fh.__exit__()
            with shp.Writer(file, window_samples=0, modify_existing=True) as fw:
                pass
            fh = shp.Reader(file, verbose=False)  # reopen file

        # missing hostname
        if "hostname" not in fh.h5file.attrs:
            print(" -> will set hostname = SheepX")
            fh.__exit__()
            with shp.Writer(file, modify_existing=True) as fw:
                fw.store_hostname("SheepX")
            fh = shp.Reader(file, verbose=False)  # reopen file

        # close file for good
        fh.__exit__()
