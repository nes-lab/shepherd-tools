# -*- coding: utf-8 -*-

"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import logging
import math
from datetime import datetime
from typing import NoReturn, Union, Dict

import numpy as np
from pathlib import Path
import h5py
from itertools import product

import samplerate as samplerate  # TODO:
from matplotlib import pyplot as plt
from scipy import signal

import pandas as pd
import yaml
from tqdm import trange

logging.basicConfig(format="%(name)s %(levelname)s: %(message)s", level=logging.INFO)
consoleHandler = logging.StreamHandler()


def unique_path(base_path: Union[str, Path], suffix: str) -> Path:
    counter = 0
    while True:
        path = base_path.with_suffix(f".{counter}{suffix}")
        if not path.exists():
            return path
        counter += 1


# SI-value [SI-Unit] = raw-value * gain + offset
general_calibration = {
    "voltage": {"gain": 3 * 1e-9, "offset": 0.0},  # allows 0 - 12 V in 3 nV-Steps
    "current": {"gain": 250 * 1e-12, "offset": 0.0},  # allows 0 - 1 A in 250 pA - Steps
    "time": {"gain": 1e-9, "offset": 0.0},
}


class Reader(object):
    """Sequentially Reads shepherd-data from HDF5 file.

    Args:
        file_path: Path of hdf5 file containing shepherd data with iv-samples, iv-curves or isc&voc
        verbose: more info during usage, 'None' skips the setter
    """

    samples_per_buffer: int = 10_000
    samplerate_sps: int = 100_000
    sample_interval_ns = int(10**9 // samplerate_sps)
    sample_interval_s: float = 1 / samplerate_sps

    max_elements: int = 100 * samplerate_sps  # per iteration (100s, ~ 300 MB RAM use)

    mode_type_dict = {
        "harvester": ["ivsample", "ivcurve", "isc_voc"],
        "emulator": ["ivsample"],
    }

    logger = logging.getLogger("SHPData.Reader")

    def __init__(self, file_path: Union[Path, None], verbose: Union[bool, None] = True):
        self._skip_open = file_path is None  # for access by writer-class
        if not self._skip_open:
            self.file_path = Path(file_path)
        if verbose is not None:
            self.logger.setLevel(logging.INFO if verbose else logging.WARNING)
        # self.logger.addHandler(consoleHandler)

        self.runtime_s = None
        self.file_size = None
        self.data_rate = None

    def __enter__(self):
        if not self._skip_open:
            self.h5file = h5py.File(self.file_path, "r")

        if self.is_valid():
            self.logger.info(f"File is available now")
        else:
            self.logger.error(
                f"File is faulty! Will try to open but there might be dragons"
            )

        self.ds_time = self.h5file["data"]["time"]
        self.ds_voltage = self.h5file["data"]["voltage"]
        self.ds_current = self.h5file["data"]["current"]
        self.cal = {
            "voltage": {
                "gain": self.ds_voltage.attrs["gain"],
                "offset": self.ds_voltage.attrs["offset"],
            },
            "current": {
                "gain": self.ds_current.attrs["gain"],
                "offset": self.ds_current.attrs["offset"],
            },
        }
        self.refresh_file_stats()

        if not self._skip_open:
            self.logger.info(
                f"Reading data from '{self.file_path}'\n"
                f"\t- runtime {self.runtime_s} s\n"
                f"\t- mode = {self.get_mode()}\n"
                f"\t- window_size = {self.get_window_samples()}\n"
                f"\t- size = {round(self.file_size/2**20)} MiB\n"
                f"\t- rate = {round(self.data_rate/2**10)} KiB/s"
            )
        return self

    def __exit__(self, *exc):
        if not self._skip_open:
            self.h5file.close()

    def refresh_file_stats(self) -> NoReturn:
        """update internal states, helpful after resampling or other changes in data-group"""
        self.h5file.flush()
        if self.ds_time.shape[0] > 1:
            self.sample_interval_ns = int(self.ds_time[1] - self.ds_time[0])
            self.samplerate_sps = int(10**9 // self.sample_interval_ns)
            self.sample_interval_s = 1.0 / self.samplerate_sps
        self.runtime_s = round(self.ds_time.shape[0] / self.samplerate_sps, 1)
        self.file_size = self.file_path.stat().st_size
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def read_buffers(
        self, start_n: int = 0, end_n: int = None, is_raw: bool = False
    ) -> tuple:
        """Generator that reads the specified range of buffers from the hdf5 file. can be configured on first call

        Args:
            :param start_n: (int) Index of first buffer to be read
            :param end_n: (int) Index of last buffer to be read
            :param is_raw: (bool) output original data, not transformed to SI-Units
        Yields:
            Buffers between start and end (tuple with time, voltage, current)
        """
        if end_n is None:
            end_n = int(self.h5file["data"]["time"].shape[0] // self.samples_per_buffer)
        self.logger.debug(f"Reading blocks from {start_n} to {end_n} from source-file")
        _raw = is_raw

        for i in range(start_n, end_n):
            idx_start = i * self.samples_per_buffer
            idx_end = idx_start + self.samples_per_buffer
            if _raw:
                yield (
                    self.ds_time[idx_start:idx_end],
                    self.ds_voltage[idx_start:idx_end],
                    self.ds_current[idx_start:idx_end],
                )
            else:
                yield (
                    self.ds_time[idx_start:idx_end] * 1e-9,
                    self.raw_to_si(
                        self.ds_voltage[idx_start:idx_end], self.cal["voltage"]
                    ),
                    self.raw_to_si(
                        self.ds_current[idx_start:idx_end], self.cal["current"]
                    ),
                )

    def get_calibration_data(self) -> dict:
        """Reads calibration-data from hdf5 file.

        :return: Calibration data as CalibrationData object
        """
        return self.cal

    def get_window_samples(self) -> int:
        if "window_samples" in self.h5file["data"].attrs.keys():
            return self.h5file["data"].attrs["window_samples"]
        return 0

    def get_mode(self) -> str:
        if "mode" in self.h5file.attrs.keys():
            return self.h5file.attrs["mode"]
        return ""

    def get_config(self) -> Dict:
        if "config" in self.h5file["data"].attrs.keys():
            return yaml.safe_load(self.h5file["data"].attrs["config"])
        return {}

    def get_hostname(self) -> str:
        if "hostname" in self.h5file.attrs.keys():
            return self.h5file.attrs["hostname"]
        return "unknown"

    def get_datatype(self) -> str:
        if "datatype" in self.h5file["data"].attrs.keys():
            return self.h5file["data"].attrs["datatype"]
        return ""

    def data_timediffs(self) -> list:
        """calculate list of (unique) time-deltas between buffers [s]
            -> optimized version that only looks at the start of each buffer

        :return: list of (unique) time-deltas between buffers [s]
        """
        iterations = math.ceil(self.h5file["data"]["time"].shape[0] / self.max_elements)
        job_iter = trange(
            0,
            self.h5file["data"]["time"].shape[0],
            self.max_elements,
            desc="timediff",
            leave=False,
            disable=iterations < 8,
        )

        def calc_timediffs(idx_start: int) -> list:
            ds_time = self.h5file["data"]["time"][
                idx_start : (idx_start + self.max_elements) : self.samples_per_buffer
            ]
            diffs_np = np.unique(ds_time[1:] - ds_time[0:-1], return_counts=False)
            return list(np.array(diffs_np))

        diffs_ll = [calc_timediffs(i) for i in job_iter]
        diffs = set(
            [
                round(float(j) * 1e-9 / self.samples_per_buffer, 6)
                for i in diffs_ll
                for j in i
            ]
        )
        return list(diffs)

    def check_timediffs(self) -> bool:
        """validate equal time-deltas -> unexpected time-jumps hint at a corrupted file or faulty measurement

        :return: True if OK
        """
        diffs = self.data_timediffs()
        if len(diffs) > 1:
            self.logger.warning(
                f"Time-jumps detected -> expected equal steps, but got: {diffs} s"
            )
        return len(diffs) <= 1

    def is_valid(self) -> bool:
        """checks file for plausibility

        :return: state of validity
        """
        # hard criteria
        if "data" not in self.h5file.keys():
            self.logger.error(f"root data-group not found (@Validator)")
            return False
        for attr in ["mode"]:
            if attr not in self.h5file.attrs.keys():
                self.logger.error(f"attribute '{attr}' not found in file (@Validator)")
                return False
            elif self.h5file.attrs["mode"] not in self.mode_type_dict:
                self.logger.error(f"unsupported mode '{self.get_mode()}' (@Validator)")
                return False
        for attr in ["window_samples", "datatype"]:
            if attr not in self.h5file["data"].attrs.keys():
                self.logger.error(
                    f"attribute '{attr}' not found in data-group (@Validator)"
                )
                return False
        for ds in ["time", "current", "voltage"]:
            if ds not in self.h5file["data"].keys():
                self.logger.error(f"dataset '{ds}' not found (@Validator)")
                return False
        for ds, attr in product(["current", "voltage"], ["gain", "offset"]):
            if attr not in self.h5file["data"][ds].attrs.keys():
                self.logger.error(
                    f"attribute '{attr}' not found in dataset '{ds}' (@Validator)"
                )
                return False
        if self.get_datatype() not in self.mode_type_dict[self.get_mode()]:
            self.logger.error(
                f"unsupported type '{self.get_datatype()}' for mode '{self.get_mode()}' (@Validator)"
            )
            return False

        if self.get_datatype() == "ivcurve" and self.get_window_samples() < 1:
            self.logger.error(
                f"window size / samples is < 1 -> invalid for ivcurves-datatype (@Validator)"
            )
            return False

        # soft-criteria:
        if self.get_datatype() != "ivcurve" and self.get_window_samples() > 0:
            self.logger.warning(
                f"window size / samples is > 0 despite not using the ivcurves-datatype (@Validator)"
            )
        # same length of datasets:
        ds_time_size = self.h5file["data"]["time"].shape[0]
        for ds in ["current", "voltage"]:
            ds_size = self.h5file["data"][ds].shape[0]
            if ds_time_size != ds_size:
                self.logger.warning(
                    f"dataset '{ds}' has different size (={ds_size}), "
                    f"compared to time-ds (={ds_time_size}) (@Validator)"
                )
        # dataset-length should be multiple of buffersize
        remaining_size = ds_time_size % self.samples_per_buffer
        if remaining_size != 0:
            self.logger.warning(
                f"datasets are not aligned with buffer-size (@Validator)"
            )
        # check compression
        for ds in ["time", "current", "voltage"]:
            comp = self.h5file["data"][ds].compression
            opts = self.h5file["data"][ds].compression_opts
            if comp not in [None, "gzip", "lzf"]:
                self.logger.warning(
                    f"unsupported compression found ({comp} != None, lzf, gzip) (@Validator)"
                )
            if (comp == "gzip") and (opts is not None) and (int(opts) > 1):
                self.logger.warning(
                    f"gzip compression is too high ({opts} > 1) for BBone (@Validator)"
                )
        return True

    def get_metadata(self, node=None, minimal: bool = False) -> dict:
        """recursive FN to capture the structure of the file

        :param node: starting node, leave free to go through whole file
        :param minimal: just provide a bare tree (much faster)
        :return: structure of that node with everything inside it
        """
        if node is None:
            self.refresh_file_stats()
            return self.get_metadata(self.h5file, minimal=minimal)

        metadata = {}
        if isinstance(node, h5py.Dataset) and not minimal:
            metadata["_dataset_info"] = {
                "dtype": str(node.dtype),
                "shape": str(node.shape),
                "chunks": str(node.chunks),
                "compression": str(node.compression),
                "compression_opts": str(node.compression_opts),
            }
            if "/data/time" == node.name:
                metadata["_dataset_info"]["time_diffs_s"] = self.data_timediffs()
            elif "int" in str(node.dtype):
                metadata["_dataset_info"]["statistics"] = self.ds_statistics(node)
        for attr in node.attrs.keys():
            attr_value = node.attrs[attr]
            if isinstance(attr_value, str):
                try:
                    attr_value = yaml.safe_load(attr_value)
                except yaml.YAMLError:
                    pass
            elif "int" in str(type(attr_value)):
                attr_value = int(attr_value)
            else:
                attr_value = float(attr_value)
            metadata[attr] = attr_value
        if isinstance(node, h5py.Group):
            if "/data" == node.name and not minimal:
                metadata["_group_info"] = {
                    "energy_Ws": self.energy(),
                    "runtime_s": round(self.runtime_s, 1),
                    "data_rate_KiB_s": round(self.data_rate / 2**10),
                    "file_size_MiB": round(self.file_size / 2**20, 3),
                    "valid": self.is_valid(),
                }
            for item in node.keys():
                metadata[item] = self.get_metadata(node[item], minimal=minimal)

        return metadata

    def save_metadata(self, node=None) -> dict:
        """get structure of file and dump content to yaml-file with same name as original

        :param node: starting node, leave free to go through whole file
        :return: structure of that node with everything inside it
        """
        yml_path = Path(self.file_path).absolute().with_suffix(".yml")
        if yml_path.exists():
            self.logger.info(f"{yml_path} already exists, will skip")
            return {}
        metadata = self.get_metadata(node)  # {"h5root": self.get_metadata(self.h5file)}
        with open(yml_path, "w") as fd:
            yaml.safe_dump(metadata, fd, default_flow_style=False, sort_keys=False)
        return metadata

    def __getitem__(self, key):
        """returns attribute or (if none found) a handle for a group or dataset (if found)

        :param key: attribute, group, dataset
        :return: value of that key, or handle of object
        """
        if key in self.h5file.attrs.keys():
            return self.h5file.attrs.__getitem__(key)
        if key in self.h5file.keys():
            return self.h5file.__getitem__(key)
        raise KeyError

    @staticmethod
    def raw_to_si(
        values_raw: Union[np.ndarray, float, int], cal: dict
    ) -> Union[np.ndarray, float]:
        """Helper to convert between physical units and raw uint values

        :param values_raw: number or numpy array with raw values
        :param cal: calibration-dict with entries for gain and offset
        :return: converted number or array
        """
        values_si = values_raw * cal["gain"] + cal["offset"]
        values_si[values_si < 0.0] = 0.0
        return values_si

    @staticmethod
    def si_to_raw(
        values_si: Union[np.ndarray, float], cal: dict
    ) -> Union[np.ndarray, int]:
        """Helper to convert between physical units and raw uint values

        :param values_si: number or numpy array with values in physical units
        :param cal: calibration-dict with entries for gain and offset
        :return: converted number or array
        """
        values_raw = (values_si - cal["offset"]) / cal["gain"]
        values_raw[values_raw < 0.0] = 0.0
        return values_raw

    def energy(self) -> float:
        """determine the recorded energy of the trace
        # multiprocessing: https://stackoverflow.com/a/71898911
        # -> failed with multiprocessing.pool and pathos.multiprocessing.ProcessPool

        :return: sampled energy in Ws (watt-seconds)
        """
        iterations = math.ceil(self.ds_time.shape[0] / self.max_elements)
        job_iter = trange(
            0,
            self.ds_time.shape[0],
            self.max_elements,
            desc="energy",
            leave=False,
            disable=iterations < 8,
        )

        def calc_energy(idx_start: int) -> float:
            idx_stop = min(idx_start + self.max_elements, self.ds_time.shape[0])
            voltage_v = self.raw_to_si(
                self.ds_voltage[idx_start:idx_stop], self.cal["voltage"]
            )
            current_a = self.raw_to_si(
                self.ds_current[idx_start:idx_stop], self.cal["current"]
            )
            return (voltage_v[:] * current_a[:]).sum() * self.sample_interval_s

        energy_ws = [calc_energy(i) for i in job_iter]
        return float(sum(energy_ws))

    def ds_statistics(self, ds: h5py.Dataset, cal: dict = None) -> dict:
        """some basic stats for a provided dataset
        :param ds: dataset to evaluate
        :param cal: calibration (if wanted)
        :return: dict with entries for mean, min, max, std
        """
        if not isinstance(cal, dict):
            if "gain" in ds.attrs.keys() and "offset" in ds.attrs.keys():
                cal = {
                    "gain": ds.attrs["gain"],
                    "offset": ds.attrs["offset"],
                    "si_converted": True,
                }
            else:
                cal = {"gain": 1, "offset": 0, "si_converted": False}
        else:
            cal["si_converted"] = True
        iterations = math.ceil(ds.shape[0] / self.max_elements)
        job_iter = trange(
            0,
            ds.shape[0],
            self.max_elements,
            desc=f"{ds.name}-stats",
            leave=False,
            disable=iterations < 8,
        )

        def calc_statistics(data: np.ndarray) -> dict:
            return {
                "mean": np.mean(data),
                "min": np.min(data),
                "max": np.max(data),
                "std": np.std(data),
            }

        stats_list = [
            calc_statistics(self.raw_to_si(ds[i : i + self.max_elements], cal))
            for i in job_iter
        ]
        if len(stats_list) < 1:
            return {}
        stats_df = pd.DataFrame(stats_list)
        stats = {  # TODO: wrong calculation for ndim-datasets with n>1
            "mean": float(stats_df.loc[:, "mean"].mean()),
            "min": float(stats_df.loc[:, "min"].min()),
            "max": float(stats_df.loc[:, "max"].max()),
            "std": float(stats_df.loc[:, "std"].mean()),
            "si_converted": cal["si_converted"],
        }
        return stats

    def save_csv(self, h5_group: h5py.Group, separator: str = ";") -> int:
        """extract numerical data via csv

        :param h5_group: can be external and should probably be downsampled
        :param separator: used between columns
        :return: number of processed entries
        """
        if h5_group["time"].shape[0] < 1:
            self.logger.warning(f"{h5_group.name} is empty, no csv generated")
            return 0
        csv_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.csv")
        if csv_path.exists():
            self.logger.warning(f"{csv_path} already exists, will skip")
            return 0
        datasets = [
            key if isinstance(h5_group[key], h5py.Dataset) else []
            for key in h5_group.keys()
        ]
        datasets.remove("time")
        datasets = ["time"] + datasets
        separator = separator.strip().ljust(2)
        header = [
            h5_group[key].attrs["description"].replace(", ", separator)
            for key in datasets
        ]
        header = separator.join(header)
        with open(csv_path, "w") as csv_file:
            csv_file.write(header + "\n")
            for idx, time_ns in enumerate(h5_group["time"][:]):
                timestamp = datetime.utcfromtimestamp(time_ns / 1e9)
                csv_file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"))
                for key in datasets[1:]:
                    values = h5_group[key][idx]
                    if isinstance(values, np.ndarray):
                        values = separator.join([str(value) for value in values])
                    csv_file.write(f"{separator}{values}")
                csv_file.write("\n")
        return h5_group["time"][:].shape[0]

    def save_log(self, h5_group: h5py.Group) -> int:
        """save dataset in group as log, optimal for logged dmesg and exceptions

        :param h5_group: can be external
        :return: number of processed entries
        """
        if h5_group["time"].shape[0] < 1:
            self.logger.warning(f"{h5_group.name} is empty, no log generated")
            return 0
        log_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.log")
        if log_path.exists():
            self.logger.warning(f"{log_path} already exists, will skip")
            return 0
        datasets = [
            key if isinstance(h5_group[key], h5py.Dataset) else []
            for key in h5_group.keys()
        ]
        datasets.remove("time")
        with open(log_path, "w") as log_file:
            for idx, time_ns in enumerate(h5_group["time"][:]):
                timestamp = datetime.utcfromtimestamp(time_ns / 1e9)
                log_file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + ":")
                for key in datasets:
                    try:
                        message = str(h5_group[key][idx])
                    except OSError:
                        message = "[[[ extractor - faulty element ]]]"
                    log_file.write(f"\t{message}")
                log_file.write("\n")
        return h5_group["time"].shape[0]

    def downsample(
        self,
        data_src: h5py.Dataset,
        data_dst: Union[None, h5py.Dataset, np.ndarray],
        start_n: int = 0,
        end_n: int = None,
        ds_factor: float = 5,
        is_time: bool = False,
    ) -> Union[h5py.Dataset, np.ndarray]:
        """Warning: only valid for IV-Stream, not IV-Curves

        :param data_src: a h5-dataset to digest, can be external
        :param data_dst: can be a dataset, numpy-array or None (will be created internally then)
        :param start_n: start-sample
        :param end_n: ending-sample (not included)
        :param ds_factor: downsampling-factor
        :param is_time: time is not really downsamples, but just decimated
        :return: downsampled h5-dataset or numpy-array
        """
        if self.get_datatype() == "ivcurve":
            self.logger.warning(f"Downsampling-Function was not written for IVCurves")
        ds_factor = max(1, math.floor(ds_factor))

        if end_n is None:
            end_n = data_src.shape[0]
        else:
            end_n = min(data_src.shape[0], round(end_n))
        start_n = min(end_n, round(start_n))
        data_len = end_n - start_n  # TODO: one-off to calculation below
        if data_len == 0:
            self.logger.warning(f"downsampling failed because of data_len = 0")
        iblock_len = min(self.max_elements, data_len)
        oblock_len = round(iblock_len / ds_factor)
        iterations = math.ceil(data_len / iblock_len)
        dest_len = math.floor(data_len / ds_factor)
        if data_dst is None:
            data_dst = np.empty((dest_len,))
        elif isinstance(data_dst, (h5py.Dataset, np.ndarray)):
            data_dst.resize((dest_len,))

        # 8th order butterworth filter for downsampling
        # note: cheby1 does not work well for static outputs (2.8V can become 2.0V for buck-converters)
        flt = signal.iirfilter(
            N=8,
            Wn=1 / max(1.1, ds_factor),
            btype="lowpass",
            output="sos",
            ftype="butter",
        )
        # filter state
        z = np.zeros((flt.shape[0], 2))

        slice_len = 0
        for i in trange(
            0,
            iterations,
            desc=f"downsampling {data_src.name}",
            leave=False,
            disable=iterations < 8,
        ):
            slice_ds = data_src[
                start_n + i * iblock_len : start_n + (i + 1) * iblock_len
            ]
            if not is_time and ds_factor > 1:
                slice_ds, z = signal.sosfilt(flt, slice_ds, zi=z)
            slice_ds = slice_ds[::ds_factor]
            slice_len = min(dest_len - i * oblock_len, oblock_len)
            data_dst[i * oblock_len : (i + 1) * oblock_len] = slice_ds[:slice_len]
        if isinstance(data_dst, np.ndarray):
            data_dst.resize(
                (oblock_len * (iterations - 1) + slice_len,), refcheck=False
            )
        else:
            data_dst.resize((oblock_len * (iterations - 1) + slice_len,))
        return data_dst

    def resample(
        self,
        data_src: h5py.Dataset,
        data_dst: Union[None, h5py.Dataset, np.ndarray],
        start_n: int = 0,
        end_n: int = None,
        samplerate_dst: float = 1000,
        is_time: bool = False,
    ) -> Union[h5py.Dataset, np.ndarray]:
        """
        :param data_src:
        :param data_dst:
        :param start_n:
        :param end_n:
        :param samplerate_dst:
        :param is_time:
        :return:
        """
        self.logger.error(
            "Resampling is still under construction - do not use for now!"
        )
        if self.get_datatype() == "ivcurve":
            self.logger.warning(f"Resampling-Function was not written for IVCurves")

        if end_n is None:
            end_n = data_src.shape[0]
        else:
            end_n = min(data_src.shape[0], round(end_n))
        start_n = min(end_n, round(start_n))
        data_len = end_n - start_n
        if data_len == 0:
            self.logger.warning(f"resampling failed because of data_len = 0")
        fs_ratio = samplerate_dst / self.samplerate_sps
        dest_len = math.floor(data_len * fs_ratio) + 1
        if fs_ratio <= 1.0:  # down-sampling
            slice_inp_len = min(self.max_elements, data_len)
            slice_out_len = round(slice_inp_len * fs_ratio)
        else:  # up-sampling
            slice_out_len = min(self.max_elements, data_len * fs_ratio)
            slice_inp_len = round(slice_out_len / fs_ratio)
        iterations = math.ceil(data_len / slice_inp_len)

        if data_dst is None:
            data_dst = np.empty((dest_len,))
        elif isinstance(data_dst, (h5py.Dataset, np.ndarray)):
            data_dst.resize((dest_len,))

        slice_inp_now = start_n
        slice_out_now = 0

        if is_time:
            for _ in trange(
                0,
                iterations,
                desc=f"resampling {data_src.name}",
                leave=False,
                disable=iterations < 8,
            ):
                tmin = data_src[slice_inp_now]
                slice_inp_now += slice_inp_len
                tmax = data_src[min(slice_inp_now, data_len - 1)]
                slice_out_ds = np.arange(
                    tmin, tmax, 1e9 / samplerate_dst
                )  # will be rounded in h5-dataset
                slice_out_nxt = slice_out_now + slice_out_ds.shape[0]
                data_dst[slice_out_now:slice_out_nxt] = slice_out_ds
                slice_out_now = slice_out_nxt
        else:
            resampler = samplerate.Resampler(
                "sinc_medium",
                channels=1,
            )  # sinc_best, _medium, _fastest or linear
            for i in trange(
                0,
                iterations,
                desc=f"resampling {data_src.name}",
                leave=False,
                disable=iterations < 8,
            ):
                slice_inp_ds = data_src[slice_inp_now : slice_inp_now + slice_inp_len]
                slice_inp_now += slice_inp_len
                slice_out_ds = resampler.process(
                    slice_inp_ds, fs_ratio, i == iterations - 1, verbose=True
                )
                # slice_out_ds = resampy.resample(slice_inp_ds, self.samplerate_sps, samplerate_dst, filter="kaiser_fast")
                slice_out_nxt = slice_out_now + slice_out_ds.shape[0]
                # print(f"@{i}: got {slice_out_ds.shape[0]}")
                data_dst[slice_out_now:slice_out_nxt] = slice_out_ds
                slice_out_now = slice_out_nxt
            resampler.reset()

        if isinstance(data_dst, np.ndarray):
            data_dst.resize((slice_out_now,), refcheck=False)
        else:
            data_dst.resize((slice_out_now,))

        return data_dst

    def generate_plot_data(
        self, start_s: float = None, end_s: float = None, relative_ts: bool = True
    ) -> Dict:
        """provides down-sampled iv-data that can be feed into plot_to_file()

        :param start_s: time in seconds, relative to start of recording
        :param end_s: time in seconds, relative to start of recording
        :param relative_ts: treat
        :return: down-sampled size of ~ self.max_elements
        """
        if self.get_datatype() == "ivcurve":
            self.logger.warning(f"Plot-Function was not written for IVCurves")
        if not isinstance(start_s, (float, int)):
            start_s = 0
        if not isinstance(end_s, (float, int)):
            end_s = self.runtime_s
        start_sample = round(start_s * self.samplerate_sps)
        end_sample = round(end_s * self.samplerate_sps)
        samplerate_dst = max(round(self.max_elements / (end_s - start_s), 3), 0.001)
        ds_factor = float(self.samplerate_sps / samplerate_dst)
        data = {
            "name": self.get_hostname(),
            "time": self.downsample(
                self.ds_time, None, start_sample, end_sample, ds_factor, is_time=True
            ).astype(float)
            * 1e-9,
            "voltage": self.raw_to_si(
                self.downsample(
                    self.ds_voltage, None, start_sample, end_sample, ds_factor
                ),
                self.cal["voltage"],
            ),
            "current": self.raw_to_si(
                self.downsample(
                    self.ds_current, None, start_sample, end_sample, ds_factor
                ),
                self.cal["current"],
            ),
            "start_s": start_s,
            "end_s": end_s,
        }
        if relative_ts:
            data["time"] = data["time"] - self.ds_time[0] * 1e-9
        return data

    @staticmethod
    def assemble_plot(
        data: Union[dict, list], width: int = 20, height: int = 10
    ) -> plt.Figure:
        """
        TODO: add power (if wanted)

        :param data: plottable / down-sampled iv-data with some meta-data -> created with generate_plot_data()
        :param width: plot-width
        :param height: plot-height
        :return:
        """
        if isinstance(data, dict):
            data = [data]
        fig, axes = plt.subplots(2, 1, sharex="all")
        fig.suptitle(f"Voltage and current")
        for date in data:
            axes[0].plot(date["time"], date["voltage"], label=date["name"])
            axes[1].plot(date["time"], date["current"] * 10**6, label=date["name"])
        axes[0].set_ylabel("voltage [V]")
        axes[1].set_ylabel(r"current [$\mu$A]")
        if len(data) > 1:
            axes[0].legend(loc="lower center", ncol=len(data))
        axes[1].set_xlabel("time [s]")
        fig.set_figwidth(width)
        fig.set_figheight(height)
        fig.tight_layout()
        return fig

    def plot_to_file(
        self,
        start_s: float = None,
        end_s: float = None,
        width: int = 20,
        height: int = 10,
    ) -> NoReturn:
        """creates (down-sampled) IV-Plot
            -> omitting start- and end-time will use the whole duration

        :param start_s: time in seconds, relative to start of recording, optional
        :param end_s: time in seconds, relative to start of recording, optional
        :param width: plot-width
        :param height: plot-height
        """
        data = [self.generate_plot_data(start_s, end_s)]

        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = self.file_path.absolute().with_suffix(
            f".plot_{start_str}_to_{end_str}.png"
        )
        if plot_path.exists():
            return

        fig = self.assemble_plot(data, width, height)
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()

    @staticmethod
    def multiplot_to_file(
        data: Union[list], plot_path: Path, width: int = 20, height: int = 10
    ) -> NoReturn:
        """creates (down-sampled) IV-Multi-Plot

        :param data: plottable / down-sampled iv-data with some meta-data -> created with generate_plot_data()
        :param plot_path: optional
        :param width: plot-width
        :param height: plot-height
        """
        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = plot_path.absolute().with_suffix(
            f".multiplot_{start_str}_to_{end_str}.png"
        )
        if plot_path.exists():
            return

        fig = Reader.assemble_plot(data, width, height)
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()


class Writer(Reader):
    """Stores data for Shepherd in HDF5 format

    Args:
        file_path: (Path) Name of the HDF5 file that data will be written to
        mode: (str) Indicates if this is data from harvester or emulator
        datatype: (str) choose type: ivsample (most common), ivcurve or isc_voc
        window_samples: (int) windows size for the datatype ivcurve
        calibration_data: (CalibrationData) Data is written as raw ADC
            values. We need calibration data in order to convert to physical
            units later.
        modify_existing: (bool) explicitly enable modifying, another file (unique name) will be created otherwise
        compression: (str) use either None, lzf or "1" (gzips compression level)
        verbose: (bool) provides more info instead of just warnings / errors
    """

    # choose lossless compression filter
    # - lzf: low to moderate compression, VERY fast, no options -> 20 % cpu overhead for half the filesize
    # - gzip: good compression, moderate speed, select level from 1-9, default is 4 -> lower levels seem fine
    #         --> _algo=number instead of "gzip" is read as compression level for gzip
    # -> comparison / benchmarks https://www.h5py.org/lzf/
    comp_default = 1
    mode_default = "harvester"
    datatype_default = "ivsample"
    cal_default = general_calibration

    chunk_shape = (Reader.samples_per_buffer,)

    logger = logging.getLogger("SHPData.Writer")

    def __init__(
        self,
        file_path: Path,
        mode: str = None,
        datatype: str = None,
        window_samples: int = None,
        calibration_data: dict = None,
        modify_existing: bool = False,
        compression: Union[None, str, int] = "default",
        verbose: Union[bool, None] = True,
    ):
        super().__init__(file_path=None, verbose=verbose)

        file_path = Path(file_path)
        self._modify = modify_existing

        if verbose is not None:
            self.logger.setLevel(logging.INFO if verbose else logging.WARNING)
        # self.logger.addHandler(consoleHandler)

        if self._modify or not file_path.exists():
            self.file_path = file_path
            self.logger.info(f"Storing data to   '{self.file_path}'")
        else:
            base_dir = file_path.resolve().parents[0]
            self.file_path = unique_path(base_dir / file_path.stem, file_path.suffix)
            self.logger.warning(
                f"File {file_path} already exists -> "
                f"storing under {self.file_path.name} instead"
            )

        if not isinstance(mode, (str, type(None))):
            raise TypeError(f"can not handle type '{type(mode)}' for mode")
        elif isinstance(mode, str) and mode not in self.mode_type_dict:
            raise ValueError(f"can not handle mode '{mode}'")

        if not isinstance(datatype, (str, type(None))):
            raise TypeError(f"can not handle type '{type(datatype)}' for datatype")
        elif (
            isinstance(datatype, str)
            and datatype
            not in self.mode_type_dict[self.mode_default if (mode is None) else mode]
        ):
            raise ValueError(f"can not handle datatype '{datatype}'")

        if self._modify:
            self.mode = mode
            self.cal = calibration_data
            self.datatype = datatype
            self.window_samples = window_samples
        else:
            self.mode = self.mode_default if (mode is None) else mode
            self.cal = (
                self.cal_default if (calibration_data is None) else calibration_data
            )
            self.datatype = self.datatype_default if (datatype is None) else datatype
            self.window_samples = 0 if (window_samples is None) else window_samples

        if compression in [None, "lzf", 1]:  # order of recommendation
            self.compression_algo = compression
        else:
            self.compression_algo = self.comp_default

    def __enter__(self):
        """Initializes the structure of the HDF5 file

        HDF5 is hierarchically structured and before writing data, we have to
        setup this structure, i.e. creating the right groups with corresponding
        data types. We will store 3 types of data in a database: The
        actual IV samples recorded either from the harvester (during recording)
        or the target (during emulation). Any log messages, that can be used to
        store relevant events or tag some parts of the recorded data.

        """
        if self._modify:
            self.h5file = h5py.File(self.file_path, "r+")
        else:
            self.h5file = h5py.File(self.file_path, "w")

            # Store voltage and current samples in the data group, both are stored as 4 Byte unsigned int
            self.data_grp = self.h5file.create_group("data")
            # the size of window_samples-attribute in harvest-data indicates ivcurves as input
            # -> emulator uses virtual-harvester
            self.data_grp.attrs[
                "window_samples"
            ] = 0  # will be adjusted by .embed_config()

            self.data_grp.create_dataset(
                "time",
                (0,),
                dtype="u8",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo,
            )
            self.data_grp["time"].attrs["unit"] = f"ns"
            self.data_grp["time"].attrs["description"] = "system time [ns]"

            self.data_grp.create_dataset(
                "current",
                (0,),
                dtype="u4",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo,
            )
            self.data_grp["current"].attrs["unit"] = "A"
            self.data_grp["current"].attrs[
                "description"
            ] = "current [A] = value * gain + offset"

            self.data_grp.create_dataset(
                "voltage",
                (0,),
                dtype="u4",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo,
            )
            self.data_grp["voltage"].attrs["unit"] = "V"
            self.data_grp["voltage"].attrs[
                "description"
            ] = "voltage [V] = value * gain + offset"

        # Store the mode in order to allow user to differentiate harvesting vs emulation data
        if isinstance(self.mode, str) and self.mode in self.mode_type_dict:
            self.h5file.attrs["mode"] = self.mode

        if (
            isinstance(self.datatype, str)
            and self.datatype in self.mode_type_dict[self.get_mode()]
        ):
            self.h5file["data"].attrs["datatype"] = self.datatype
        elif not self._modify:
            self.logger.error(f"datatype invalid? '{self.datatype}' not written")

        if isinstance(self.window_samples, int):
            self.h5file["data"].attrs["window_samples"] = self.window_samples

        if self.cal is not None:
            for channel, parameter in product(
                ["current", "voltage"], ["gain", "offset"]
            ):
                self.h5file["data"][channel].attrs[parameter] = self.cal[channel][
                    parameter
                ]

        super().__enter__()
        return self

    def __exit__(self, *exc):
        self._align()
        self.refresh_file_stats()
        self.logger.info(
            f"closing hdf5 file, {self.runtime_s} s iv-data, "
            f"size = {round(self.file_size/2**20, 3)} MiB, "
            f"rate = {round(self.data_rate/2**10)} KiB/s"
        )
        self.is_valid()
        self.h5file.close()

    def append_iv_data_raw(
        self,
        timestamp_ns: Union[np.ndarray, float, int],
        voltage: np.ndarray,
        current: np.ndarray,
    ) -> NoReturn:
        """Writes raw data to database

        Args:
            timestamp_ns: just start of buffer or whole ndarray
            voltage: ndarray as raw uint values
            current: ndarray as raw uint values
        """
        len_new = min(voltage.size, current.size)

        if isinstance(timestamp_ns, float):
            timestamp_ns = int(timestamp_ns)
        if isinstance(timestamp_ns, int):
            time_series_ns = self.sample_interval_ns * np.arange(len_new).astype("u8")
            timestamp_ns = timestamp_ns + time_series_ns
        if isinstance(timestamp_ns, np.ndarray):
            len_new = min(len_new, timestamp_ns.size)
        else:
            self.logger.error(f"timestamp-data was not usable")
            return

        len_old = self.ds_time.shape[0]

        # resize dataset
        self.ds_time.resize((len_old + len_new,))
        self.ds_voltage.resize((len_old + len_new,))
        self.ds_current.resize((len_old + len_new,))

        # append new data
        self.ds_time[len_old : len_old + len_new] = timestamp_ns[:len_new]
        self.ds_voltage[len_old : len_old + len_new] = voltage[:len_new]
        self.ds_current[len_old : len_old + len_new] = current[:len_new]

    def append_iv_data_si(
        self,
        timestamp: Union[np.ndarray, float],
        voltage: np.ndarray,
        current: np.array,
    ) -> NoReturn:
        """Writes data (in SI / physical unit) to file, but converts it to raw-data first

        Args:
            timestamp: python timestamp (time.time()) in seconds (si-unit) -> just start of buffer or whole ndarray
            voltage: ndarray in physical-unit V
            current: ndarray in physical-unit A
        """
        # SI-value [SI-Unit] = raw-value * gain + offset,
        timestamp = timestamp * 10**9
        voltage = self.si_to_raw(voltage, self.cal["voltage"])
        current = self.si_to_raw(current, self.cal["current"])
        self.append_iv_data_raw(timestamp, voltage, current)

    def _align(self) -> NoReturn:
        """Align datasets with buffer-size of shepherd"""
        self.refresh_file_stats()
        n_buff = self.ds_time.size / self.samples_per_buffer
        size_new = int(math.floor(n_buff) * self.samples_per_buffer)
        if size_new < self.ds_time.size:
            if self.samplerate_sps < 95_000:
                self.logger.debug(f"skipped alignment due to altered samplerate")
                return
            self.logger.info(
                f"aligning with buffer-size, discarding last {self.ds_time.size - size_new} entries"
            )
            self.ds_time.resize((size_new,))
            self.ds_voltage.resize((size_new,))
            self.ds_current.resize((size_new,))

    def __setitem__(self, key, item):
        """Offer a convenient interface to store any relevant key-value data (attribute) of H5-file-structure"""
        return self.h5file.attrs.__setitem__(key, item)

    def set_config(self, data: dict) -> NoReturn:
        """Important Step to get a self-describing Output-File

        :param data: from virtual harvester or converter / source
        """
        self.h5file["data"].attrs["config"] = yaml.dump(data, default_flow_style=False)
        if "window_samples" in data:
            self.set_window_samples(data["window_samples"])

    def set_window_samples(self, samples: int = 0) -> NoReturn:
        self.h5file["data"].attrs["window_samples"] = samples

    def set_hostname(self, name: str) -> NoReturn:
        self.h5file.attrs["hostname"] = name
