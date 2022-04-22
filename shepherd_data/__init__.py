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

from matplotlib import pyplot as plt
from scipy import signal

import pandas as pd
import yaml
from tqdm import trange

consoleHandler = logging.StreamHandler()
logger = logging.getLogger("shepherd")
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)


def unique_path(base_path: Union[str, Path], suffix: str):
    counter = 0
    while True:
        path = base_path.with_suffix(f".{counter}{suffix}")
        if not path.exists():
            return path
        counter += 1


# SI-value [SI-Unit] = raw-value * gain + offset
general_calibration = {
    "voltage": {"gain": 3 * 1e-9, "offset": 0.0},      # allows 0 - 12 V in 3 nV-Steps
    "current": {"gain": 250 * 1e-12, "offset": 0.0},   # allows 0 - 1 A in 250 pA - Steps
    "time": {"gain": 1e-9, "offset": 0.0},
}


class ShepherdReader(object):
    """ Sequentially Reads data from HDF5 file.

    Args:
        file_path (Path): Path of hdf5 file containing IV data
    """

    samples_per_buffer: int = 10_000
    samplerate_sps: int = 100_000
    sample_interval_ns = int(10 ** 9 // samplerate_sps)
    sample_interval_s: float = (1 / samplerate_sps)

    max_elements: int = 100 * samplerate_sps  # per iteration (100s, ~ 300 MB RAM use)
    dev = "ShpReader"

    def __init__(self, file_path: Union[Path, None], verbose: bool = True):
        self._skip_read = file_path is None  # for access by writer-class
        if not self._skip_read:
            self.file_path = file_path
        logger.setLevel(logging.INFO if verbose else logging.WARNING)
        self.runtime_s = None
        self.file_size = None
        self.data_rate = None

    def __enter__(self):
        if not self._skip_read:
            self._h5file = h5py.File(self.file_path, "r", swmr=True)

        if self.is_valid():
            logger.info(f"[{self.dev}] File is available now")
        else:
            raise ValueError(f"[{self.dev}] File was faulty, will not Open")

        self.ds_time = self._h5file["data"]["time"]
        self.ds_voltage = self._h5file["data"]["voltage"]
        self.ds_current = self._h5file["data"]["current"]
        self.cal = {
            "voltage": {"gain": self.ds_voltage.attrs["gain"], "offset": self.ds_voltage.attrs["offset"]},
            "current": {"gain": self.ds_current.attrs["gain"], "offset": self.ds_current.attrs["offset"]},
        }
        self.refresh_file_stats()

        if not self._skip_read:
            logger.info(
                f"[{self.dev}] Reading data from '{self.file_path}'\n"
                f"\t- runtime {self.runtime_s} s\n"
                f"\t- mode = {self.get_mode()}\n"
                f"\t- window_size = {self.get_window_samples()}\n"
                f"\t- size = {round(self.file_size/2**20)} MiB\n"
                f"\t- rate = {round(self.data_rate/2**10)} KiB/s")
        return self

    def __exit__(self, *exc):
        if not self._skip_read:
            self._h5file.close()

    def refresh_file_stats(self):
        self._h5file.flush()
        self.runtime_s = round(self.ds_time.shape[0] / self.samplerate_sps, 1)
        self.file_size = self.file_path.stat().st_size
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def read_buffers(self, start: int = 0, end: int = None, raw: bool = False):
        """Reads the specified range of buffers from the hdf5 file.

        Args:
            :param start: (int): Index of first buffer to be read
            :param end: (int): Index of last buffer to be read
            :param raw: output original data, not transformed to SI-Units
        Yields:
            Buffers between start and end (tuple with time, voltage, current)
        """
        if end is None:
            end = int(self._h5file["data"]["time"].shape[0] // self.samples_per_buffer)
        logger.debug(f"[{self.dev}] Reading blocks from {start} to {end} from source-file")
        _raw = raw

        for i in range(start, end):
            idx_start = i * self.samples_per_buffer
            idx_end = idx_start + self.samples_per_buffer
            if _raw:
                yield (self.ds_time[idx_start:idx_end],
                       self.ds_voltage[idx_start:idx_end],
                       self.ds_current[idx_start:idx_end])
            else:
                yield (self.ds_time[idx_start:idx_end] * 1e-9,
                       self.raw_to_si(self.ds_voltage[idx_start:idx_end], self.cal["voltage"]),
                       self.raw_to_si(self.ds_current[idx_start:idx_end], self.cal["current"]))

    def get_calibration_data(self) -> dict:
        """Reads calibration data from hdf5 file.

        Returns:
            Calibration data as CalibrationData object
        """
        return self.cal

    def get_window_samples(self) -> int:
        if "window_samples" in self._h5file["data"].attrs.keys():
            return self._h5file["data"].attrs["window_samples"]
        return 0

    def get_mode(self) -> str:
        if "mode" in self._h5file.attrs.keys():
            return self._h5file.attrs["mode"]
        return ""

    def get_config(self) -> Dict:
        if "config" in self._h5file["data"].attrs.keys():
            return yaml.safe_load(self._h5file["data"].attrs["config"])
        return {}

    def data_timediffs(self) -> list:
        """ calculate list of (unique) time-deltas between buffers [s]
            -> optimized version that only looks at the start of each buffer
            TODO: consumes ~6 GiB RAM (24h data) and has no progressbar -> ~ 2min
        """
        ds_time = self._h5file["data"]["time"][::1*self.samples_per_buffer]
        diffs = np.unique(ds_time[1:] - ds_time[0:-1], return_counts=False)
        diffs = list(np.array(diffs))
        diffs = [float(i) * 1e-9 for i in diffs]
        return diffs

    def is_valid(self) -> bool:
        """ checks file for plausibility
        :return: state of validity
        """
        # hard criteria
        if "data" not in self._h5file.keys():
            logger.error(f"[{self.dev}|validator] root data-group not found")
            return False
        for attr in ["mode"]:
            if attr not in self._h5file.attrs.keys():
                logger.error(f"[{self.dev}|validator] attribute '{attr}' in file not found")
                return False
        for attr in ["window_samples"]:
            if attr not in self._h5file["data"].attrs.keys():
                logger.error(f"[{self.dev}|validator] attribute '{attr}' in data-group not found")
                return False
        for ds in ["time", "current", "voltage"]:
            if ds not in self._h5file["data"].keys():
                logger.error(f"[{self.dev}|validator] dataset '{ds}' not found")
                return False
        for ds, attr in product(["current", "voltage"], ["gain", "offset"]):
            if attr not in self._h5file["data"][ds].attrs.keys():
                logger.error(f"[{self.dev}|validator] attribute '{attr}' in dataset '{ds}' not found")
                return False

        # soft-criteria:
        # same length of datasets:
        ds_time_size = self._h5file["data"]["time"].shape[0]
        for ds in ["current", "voltage"]:
            ds_size = self._h5file["data"][ds].shape[0]
            if ds_time_size != ds_size:
                logger.error(f"[{self.dev}|validator] dataset '{ds}' has different size (={ds_size}), "
                             f"compared to time-ds (={ds_time_size})")
        # dataset-length should be multiple of buffersize
        remaining_size = ds_time_size % self.samples_per_buffer
        if remaining_size != 0:
            logger.error(f"[{self.dev}|validator] datasets are not aligned with buffer-size")
        # check compression
        for ds in ["time", "current", "voltage"]:
            comp = self._h5file["data"][ds].compression
            opts = self._h5file["data"][ds].compression_opts
            if comp not in [None, "gzip", "lzf"]:
                logger.error(f"[{self.dev}|validator] unsupported compression found ({comp} != None, lzf, gzip)")
            if (comp == "gzip") and (opts is not None) and (int(opts) > 1):
                logger.error(f"[{self.dev}|validator] gzip compression is too high ({opts} > 1) for BBone")
        return True

    def get_metadata(self, node=None) -> dict:
        """ recursive FN to capture the structure of the file
        :param node: starting node, leave free to go through whole file
        :return: structure of that node everything inside it
        """
        # recursive...
        if node is None:
            self.refresh_file_stats()
            return self.get_metadata(self._h5file)

        metadata = {}
        if isinstance(node, h5py.Dataset):
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
            if "/data" == node.name:
                metadata["_group_info"] = {
                    "energy_Ws": self.energy(),
                    "runtime_s": round(self.runtime_s, 1),
                    "data_rate_KiB_s": round(self.data_rate / 2**10),
                    "file_size_MiB": round(self.file_size / 2**20, 3),
                    "valid": self.is_valid(),
                }
            for item in node.keys():
                metadata[item] = self.get_metadata(node[item])

        return metadata

    def save_metadata(self, node=None) -> dict:
        """ get structure of file and dump content to yaml-file with same name as original
        :param node: starting node, leave free to go through whole file
        """
        yml_path = Path(self.file_path).absolute().with_suffix(".yml")
        if yml_path.exists():
            logger.info(f"[{self.dev}] {yml_path} already exists, will skip")
            return {}
        metadata = self.get_metadata()  # {"h5root": self.get_metadata(self._h5file)}
        with open(yml_path, "w") as fd:
            yaml.safe_dump(metadata, fd, default_flow_style=False, sort_keys=False)
        return metadata

    def __getitem__(self, key):
        """ returns attribute or (if none found) a handle for a group or dataset (if found)

        :param key: attribute, group, dataset
        :return: value of that key, or handle of object
        """
        if key in self._h5file.attrs.keys():
            return self._h5file.attrs.__getitem__(key)
        if key in self._h5file.keys():
            return self._h5file.__getitem__(key)
        raise KeyError

    @staticmethod
    def raw_to_si(values_raw: np.ndarray, cal: dict) -> np.ndarray:
        values_si = values_raw * cal["gain"] + cal["offset"]
        values_si[values_si < 0.0] = 0.0
        return values_si

    @staticmethod
    def si_to_raw(values_si: np.ndarray, cal: dict) -> np.ndarray:
        values_raw = (values_si - cal["offset"]) / cal["gain"]
        values_raw[values_raw < 0.0] = 0.0
        return values_raw

    def _energy_calc(self, idx_start: int):
        idx_stop = min(idx_start + self.max_elements, self.ds_time.shape[0])
        voltage_v = self.raw_to_si(self.ds_voltage[idx_start:idx_stop], self.cal["voltage"])
        current_a = self.raw_to_si(self.ds_current[idx_start:idx_stop], self.cal["current"])
        return (voltage_v[:] * current_a[:]).sum() * self.sample_interval_s

    def energy(self) -> float:
        """ determine the recorded energy of the trace
        # multiprocessing: https://stackoverflow.com/a/71898911
        # -> failed with multiprocessing.pool and pathos.multiprocessing.ProcessPool
        :return: sampled energy in Ws (watt-seconds)
        """
        iterations = math.ceil(self.ds_time.shape[0] / self.max_elements)
        job_iter = trange(0, self.ds_time.shape[0], self.max_elements, desc="energy", leave=False, disable=iterations < 8)
        energy_ws = [self._energy_calc(i) for i in job_iter]
        return float(sum(energy_ws))

    @staticmethod
    def _ds_statistics_calc(ds: np.ndarray) -> dict:
        return {"mean": np.mean(ds),
                "min": np.min(ds),
                "max": np.max(ds),
                "std": np.std(ds),
                }

    def ds_statistics(self, ds: h5py.Dataset, cal: dict = None) -> dict:
        """ some basic stats for a provided dataset
        :param ds: dataset to evaluate
        :param cal: calibration (if wanted)
        :return: dict with entries for mean, min, max, std
        """
        if not isinstance(cal, dict):
            if "gain" in ds.attrs.keys() and "offset" in ds.attrs.keys():
                cal = {"gain": ds.attrs["gain"], "offset": ds.attrs["offset"], "cal_converted": True}
            else:
                cal = {"gain": 1, "offset": 0, "cal_converted": False}
        else:
            cal["cal_converted"] = True
        iterations = math.ceil(ds.shape[0] / self.max_elements)
        job_iter = trange(0, ds.shape[0], self.max_elements, desc=f"{ds.name}-stats", leave=False, disable=iterations < 8)
        stats_list = [self._ds_statistics_calc(self.raw_to_si(ds[i:i + self.max_elements], cal)) for i in job_iter]
        if len(stats_list) < 1:
            return {}
        stats_df = pd.DataFrame(stats_list)
        stats = { # TODO: wrong calculation for ndim-datasets with n>1
            "mean": float(stats_df.loc[:, "mean"].mean()),
            "min": float(stats_df.loc[:, "min"].min()),
            "max": float(stats_df.loc[:, "max"].max()),
            "std": float(stats_df.loc[:, "std"].mean()),
            "cal_converted": cal["cal_converted"]
        }
        return stats

    def save_csv(self, h5_group: h5py.Group, separator: str = ";") -> int:
        if h5_group["time"].shape[0] < 1:
            logger.info(f"[{self.dev}] {h5_group.name} is empty, no csv generated")
            return 0
        csv_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.csv")
        if csv_path.exists():
            logger.info(f"[{self.dev}] {csv_path} already exists, will skip")
            return 0
        datasets = [key if isinstance(h5_group[key], h5py.Dataset) else [] for key in h5_group.keys()]
        datasets.remove("time")
        datasets = ["time"] + datasets
        separator = separator.strip().ljust(2)
        header = [h5_group[key].attrs["description"].replace(", ", separator) for key in datasets]
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
        """ save dataset in group as log, optimal for logged dmesg and exceptions

        :param h5_group:
        :return:
        """
        if h5_group["time"].shape[0] < 1:
            logger.info(f"[{self.dev}] {h5_group.name} is empty, no log generated")
            return 0
        log_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.log")
        if log_path.exists():
            logger.info(f"[{self.dev}] {log_path} already exists, will skip")
            return 0
        datasets = [key if isinstance(h5_group[key], h5py.Dataset) else [] for key in h5_group.keys()]
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

    def downsample(self, dataset: h5py.Dataset, start: int, end: int, ds_factor: float = 5, is_time: bool = False):
        """
        :param dataset:
        :param ds_factor:
        :param is_time:
        :return:
        """
        ds_factor = max(1, math.floor(ds_factor))
        start = min(dataset.shape[0], round(start))
        end = min(dataset.shape[0], round(end))
        data_len = end - start  # TODO: one-off to calculation below
        iblock_len = min(self.max_elements, data_len)
        oblock_len = round(iblock_len / ds_factor)
        iterations = math.ceil(data_len / iblock_len)
        dest_len = math.floor(data_len / ds_factor)
        dest_ds = np.empty((dest_len,))

        if not is_time and ds_factor > 1:
            # 8th order butterworth filter for downsampling
            # note: cheby1 does not work well for static outputs (2.8V can become 2.0V for buck-converters)
            flt = signal.iirfilter(
                N=8,
                Wn=1 / ds_factor,
                btype="lowpass",
                output="sos",
                ftype="butter",
            )
            # filter state
            z = np.zeros((flt.shape[0], 2))

        slice_len = 0
        for i in trange(0, iterations, desc=f"downsampling {dataset.name}", leave=False, disable=iterations < 8):
            slice_ds = dataset[start + i * iblock_len: start + (i + 1) * iblock_len]
            if not is_time and ds_factor > 1:
                slice_ds, z = signal.sosfilt(flt, slice_ds, zi=z)
            slice_ds = slice_ds[::ds_factor]
            slice_len = min(dest_len - i * oblock_len, oblock_len)
            dest_ds[i * oblock_len: (i + 1) * oblock_len] = slice_ds[:slice_len]
        dest_ds.resize((oblock_len*(iterations-1) + slice_len,))
        return dest_ds

    def plot_to_file(self, start_s: float = None, end_s: float = None):
        """

        :param start_s:
        :param end_s:
        :return:
        """
        if not isinstance(start_s, (float, int)):
            start_s = 0
        if not isinstance(end_s, (float, int)):
            end_s = self.runtime_s
        start_str = f"{start_s:.3f}".replace(".", "s")
        end_str = f"{end_s:.3f}".replace(".", "s")
        plot_path = self.file_path.with_suffix(f".{start_str}_to_{end_str}.png")
        if plot_path.exists():
            return
        start_sample = round(start_s * self.samplerate_sps)
        end_sample = round(end_s * self.samplerate_sps)
        # goal: downsample-size of self.max_elements
        sampling_rate = max(round(self.max_elements/(end_s - start_s), 3), 0.001)
        ds_factor = float(self.samplerate_sps / sampling_rate)
        data = {
            "time": self.downsample(self.ds_time, start_sample, end_sample, ds_factor, is_time=True).astype(float) * 1e-9,
            "voltage": self.raw_to_si(self.downsample(self.ds_voltage, start_sample, end_sample, ds_factor), self.cal["voltage"]),
            "current": self.raw_to_si(self.downsample(self.ds_current, start_sample, end_sample, ds_factor), self.cal["current"]),
        }
        time_zero = float(self.ds_time[0]) * 1e-9
        fig, axes = plt.subplots(2, 1, sharex=True)
        fig.suptitle(f"Voltage and current")
        axes[0].plot(data["time"] - time_zero, data["voltage"])  # add: ,label=active_node
        axes[1].plot(data["time"] - time_zero, data["current"] * 10**6)
        active_nodes = ["TheHost"]  # TODO: get hostname
        axes[0].set_ylabel("voltage [V]")
        axes[1].set_ylabel(r"current [$\mu$A]")
        axes[0].legend(loc="lower center", ncol=len(active_nodes))
        axes[1].set_xlabel("time [s]")
        fig.set_figwidth(20)  # TODO: make userdef, limit x to start and end
        fig.set_figheight(10)
        fig.tight_layout()
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()  # TODO: add other nodes


class ShepherdWriter(ShepherdReader):
    """Stores data for Shepherd in HDF5 format

    Args:
        file_path (Path): Name of the HDF5 file that data will be written to

        mode (str): Indicates if this is data from harvester or emulator
        calibration_data (CalibrationData): Data is written as raw ADC
            values. We need calibration data in order to convert to physical
            units later.
        modify_existing (bool): explicitly enable modifying, another file (unique name) will be created otherwise
        compression (str): use either None, lzf, gzip or gzips compression level from 1-9

    """

    # choose lossless compression filter
    # - lzf: low to moderate compression, VERY fast, no options -> 20 % cpu overhead for half the filesize
    # - gzip: good compression, moderate speed, select level from 1-9, default is 4 -> lower levels seem fine
    #         --> _algo=number instead of "gzip" is read as compression level for gzip
    # -> comparison / benchmarks https://www.h5py.org/lzf/
    comp_default = 1
    mode_default = "harvester"
    cal_default = general_calibration

    chunk_shape = (ShepherdReader.samples_per_buffer,)

    def __init__(
            self,
            file_path: Path,
            mode: str = None,
            calibration_data: dict = None,
            modify_existing: bool = False,
            compression: Union[None, str, int] = "default",
            verbose: bool = True,
    ):
        super().__init__(file_path=None, verbose=verbose)
        self.dev = "ShpWriter"

        file_path = Path(file_path)
        self._modify = modify_existing

        if self._modify or not file_path.exists():
            self.file_path = file_path
            logger.info(f"[{self.dev}] Storing data to   '{self.file_path}'")
        else:
            base_dir = file_path.resolve().parents[0]
            self.file_path = unique_path(
                base_dir / file_path.stem, file_path.suffix
            )
            logger.warning(
                f"[{self.dev}] File {file_path} already exists.. "
                f"storing under {self.file_path} instead"
            )

        if self._modify:
            self.mode = mode
            self.cal = calibration_data
        else:
            self.mode = self.mode_default if (mode is None) else mode
            self.cal = self.cal_default if (calibration_data is None) else calibration_data

        if compression in [None, "lzf", 1]:  # order of recommendation
            self.compression_algo = compression
        else:
            self.compression_algo = self.comp_default

    def __enter__(self):
        """Initializes the structure of the HDF5 file

        HDF5 is hierarchically structured and before writing data, we have to
        setup this structure, i.e. creating the right groups with corresponding
        data types. We will store 3 types of data in a LogWriter database: The
        actual IV samples recorded either from the harvester (during recording)
        or the target (during emulation). Any log messages, that can be used to
        store relevant events or tag some parts of the recorded data. And lastly
        the state of the GPIO pins.

        """
        if self._modify:
            self._h5file = h5py.File(self.file_path, "r+")
        else:
            self._h5file = h5py.File(self.file_path, "w")

            # Store voltage and current samples in the data group, both are stored as 4 Byte unsigned int
            self.data_grp = self._h5file.create_group("data")
            # the size of window_samples-attribute in harvest-data indicates ivcurves as input
            # -> emulator uses virtual-harvester
            self.data_grp.attrs["window_samples"] = 0  # will be adjusted by .embed_config()

            self.data_grp.create_dataset(
                "time",
                (0,),
                dtype="u8",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo)
            self.data_grp["time"].attrs["unit"] = f"ns"
            self.data_grp["time"].attrs["description"] = "system time [ns]"

            self.data_grp.create_dataset(
                "current",
                (0,),
                dtype="u4",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo)
            self.data_grp["current"].attrs["unit"] = "A"
            self.data_grp["current"].attrs["description"] = "current [A] = value * gain + offset"

            self.data_grp.create_dataset(
                "voltage",
                (0,),
                dtype="u4",
                maxshape=(None,),
                chunks=self.chunk_shape,
                compression=self.compression_algo)
            self.data_grp["voltage"].attrs["unit"] = "V"
            self.data_grp["voltage"].attrs["description"] = "voltage [V] = value * gain + offset"

        # Store the mode in order to allow user to differentiate harvesting vs emulation data
        if self.mode is not None:
            self._h5file.attrs["mode"] = self.mode

        if self.cal is not None:
            for channel, parameter in product(["current", "voltage"], ["gain", "offset"]):
                self.data_grp[channel].attrs[parameter] = self.cal[channel][parameter]

        super().__enter__()
        return self

    def __exit__(self, *exc):
        self.align()
        self.refresh_file_stats()
        logger.info(f"[{self.dev}] closing hdf5 file, {self.runtime_s} s iv-data, "
                    f"size = {round(self.file_size/2**20, 3)} MiB, "
                    f"rate = {round(self.data_rate/2**10)} KiB/s")
        self._h5file.close()

    def append_iv_data_raw(self, timestamp_ns, voltage: np.ndarray, current: np.ndarray) -> NoReturn:
        """Writes data to file.

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
            logger.error(f"[{self.dev}] timestamp-data was not usable")
            return

        len_old = self.ds_time.shape[0]

        # resize dataset
        self.ds_time.resize((len_old + len_new,))
        self.ds_voltage.resize((len_old + len_new,))
        self.ds_current.resize((len_old + len_new,))

        # append new data
        self.ds_time[len_old:len_old + len_new] = timestamp_ns[:len_new]
        self.ds_voltage[len_old:len_old + len_new] = voltage[:len_new]
        self.ds_current[len_old:len_old + len_new] = current[:len_new]

    def append_iv_data_si(self, timestamp, voltage: np.ndarray, current: np.array) -> NoReturn:
        """ Writes data to file, but converts it to raw-data first

        Args:
            timestamp: python timestamp (time.time()) in seconds (si-unit)
            voltage: ndarray in si-units
            current: ndarray in si-units

        Returns:

        """
        # SI-value [SI-Unit] = raw-value * gain + offset,
        timestamp = timestamp * 10**9
        voltage = self.si_to_raw(voltage, self.cal["voltage"])
        current = self.si_to_raw(current, self.cal["current"])
        self.append_iv_data_raw(timestamp, voltage, current)

    def align(self) -> NoReturn:
        """ Align datasets with buffer-size of shepherd
        TODO: make default at exit?
        """
        n_buff = self.ds_time.size / self.samples_per_buffer
        size_new = int(math.floor(n_buff) * self.samples_per_buffer)
        if size_new < self.ds_time.size:
            logger.info(f"[{self.dev}] aligning with buffer-size, discarding last {self.ds_time.size - size_new} entries")
            self.ds_time.resize((size_new,))
            self.ds_voltage.resize((size_new,))
            self.ds_current.resize((size_new,))

    def __setitem__(self, key, item):
        """Offer a convenient interface to store any relevant key-value data (attribute) of H5-file-structure"""
        return self._h5file.attrs.__setitem__(key, item)

    def set_config(self, data: dict) -> NoReturn:
        """
        Important Step to get a self-describing Output-File
        Note: the size of window_samples-attribute in harvest-data indicates ivcurves as input
        -> emulator uses virtual-harvester

        :param data: from virtual harvester or converter / source
        :return: None
        """
        self.data_grp.attrs["config"] = yaml.dump(data, default_flow_style=False)
        if "window_samples" in data:
            self.data_grp.attrs["window_samples"] = data["window_samples"]

    def set_window_samples(self, samples: int = 0) -> NoReturn:
        self.data_grp.attrs["window_samples"] = samples
