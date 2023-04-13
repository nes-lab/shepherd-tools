"""
script will:
- iterate through this directory and
- try to find and fix errors in hdf5-files / shepherd-recordings
- old recordings from shepherd 1.x can be made available for v2.x

-> the usage of __enter__() and __exit__() is not encouraged,
   but makes the codes simpler for this edge-case (reading- and writing-handler for same file)
"""
import os
from pathlib import Path

import shepherd_data as shp

if __name__ == "__main__":
    flist = os.listdir("./")
    for file in flist:
        fpath = Path(file)
        if not fpath.is_file() or ".h5" != fpath.suffix:
            continue
        print(f"Analyzing '{fpath.name}' ...")
        with shp.Reader(fpath, verbose=False) as fh:
            elements = fh.get_metadata(minimal=True)

            # hard criteria to detect shepherd-recording (and sort out other hdf5-files)
            if "data" not in elements:
                continue
            for dset in ["time", "current", "voltage"]:
                if dset not in elements["data"]:
                    continue

            # datasets with unequal size
            ds_time_size = fh.h5file["data"]["time"].shape[0]
            for dset in ["current", "voltage"]:
                ds_size = fh.h5file["data"][dset].shape[0]
                if ds_time_size != ds_size:
                    print(" -> will bring datasets to equal size")
                    fh.__exit__()
                    with shp.Writer(fpath, modify_existing=True) as fw:
                        fw.h5file["data"]["time"].resize(min(ds_time_size, ds_size))
                        fw.h5file["data"][dset].resize(min(ds_time_size, ds_size))
                    fh.__enter__()

            # unaligned datasets
            remaining_size = fh.h5file["data"]["time"].shape[0] % fh.samples_per_buffer
            if remaining_size != 0:
                print(" -> will align datasets")
                fh.__exit__()
                with shp.Writer(fpath, modify_existing=True) as fw:
                    pass
                fh.__enter__()

            # invalid modes
            mode = fh.get_mode()
            if mode not in shp.Reader.mode_dtype_dict:
                mode = shp.Writer.mode_default
                if "har" in fh.get_mode():  # can be harvest, harvesting, ...
                    mode = "harvester"
                elif "emu" in fh.get_mode():  # can be emulation, emulate
                    mode = "emulator"
                print(f" -> will set mode = {mode}")
                fh.__exit__()
                with shp.Writer(fpath, mode=mode, modify_existing=True) as fw:
                    pass
                fh.__enter__()

            # invalid datatype
            datatype = fh.get_datatype()
            if datatype not in shp.Reader.mode_dtype_dict[mode]:
                datatype = shp.Writer.datatype_default
                if "curv" in fh.get_datatype():
                    datatype = "ivcurve"
                print(f" -> will set datatype = {datatype}")
                fh.__exit__()
                with shp.Writer(fpath, datatype=datatype, modify_existing=True) as fw:
                    pass
                fh.__enter__()

            # missing window_samples
            if "window_samples" not in fh.h5file["data"].attrs.keys():
                if datatype == "ivcurve":
                    print("Window size missing, but ivcurves detected -> no repair")
                    continue
                print(" -> will set window size = 0")
                fh.__exit__()
                with shp.Writer(fpath, window_samples=0, modify_existing=True) as fw:
                    pass
                fh.__enter__()

            # missing hostname
            if "hostname" not in fh.h5file.attrs.keys():
                print(" -> will set hostname = SheepX")
                fh.__exit__()
                with shp.Writer(fpath, modify_existing=True) as fw:
                    fw.set_hostname("SheepX")
                fh.__enter__()
