"""
Reader-Baseclass
"""
import contextlib
import errno
import logging
import math
import os
from itertools import product
from pathlib import Path
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Union

import h5py
import numpy as np
import yaml
from pydantic import validate_call
from tqdm import trange

from .commons import samplerate_sps_default
from .data_models.base.calibration import CalibrationPair
from .data_models.base.calibration import CalibrationSeries
from .data_models.content.energy_environment import EnergyDType


class BaseReader:
    """Sequentially Reads shepherd-data from HDF5 file.

    Args:
        file_path: Path of hdf5 file containing shepherd data with iv-samples, iv-curves or isc&voc
        verbose: more info during usage, 'None' skips the setter
    """

    samples_per_buffer: int = 10_000

    mode_dtype_dict = {
        "harvester": [
            EnergyDType.ivsample,
            EnergyDType.ivcurve,
            EnergyDType.isc_voc,
        ],
        "emulator": [EnergyDType.ivsample],
    }

    @validate_call
    def __init__(self, file_path: Optional[Path], verbose: Optional[bool] = True):
        if not hasattr(self, "file_path"):
            self.file_path: Optional[Path] = None
            if isinstance(file_path, (Path, str)):
                self.file_path = Path(file_path).resolve()

        if not hasattr(self, "_logger"):
            self._logger: logging.Logger = logging.getLogger("SHPCore.Reader")
        if verbose is not None:
            self._logger.setLevel(logging.INFO if verbose else logging.WARNING)

        if not hasattr(self, "samplerate_sps"):
            self.samplerate_sps: int = samplerate_sps_default
        self.sample_interval_ns: int = int(10**9 // self.samplerate_sps)
        self.sample_interval_s: float = 1 / self.samplerate_sps

        self.max_elements: int = 40 * self.samplerate_sps
        # ⤷ per iteration (40s full res, < 200 MB RAM use)

        # init stats
        self.runtime_s: float = 0
        self.file_size: int = 0
        self.data_rate: float = 0

        # open file (if not already done by writer)
        self._reader_opened: bool = False
        if not hasattr(self, "h5file"):
            if not isinstance(self.file_path, Path):
                raise TypeError("Provide a valid Path-Object to Reader!")
            if not (self.file_path.exists() and self.file_path.is_file()):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), self.file_path.name
                )

            self.h5file = h5py.File(self.file_path, "r")  # = readonly
            self._reader_opened = True

            if self.is_valid():
                self._logger.info("File is available now")
            else:
                self._logger.error(
                    "File is faulty! Will try to open but there might be dragons",
                )

        if not isinstance(self.h5file, h5py.File):
            raise TypeError("Type of opened file is not h5py.File")

        self.ds_time: h5py.Dataset = self.h5file["data"]["time"]
        self.ds_voltage: h5py.Dataset = self.h5file["data"]["voltage"]
        self.ds_current: h5py.Dataset = self.h5file["data"]["current"]

        # retrieve cal-data
        if not hasattr(self, "_cal"):
            cal_dict = CalibrationSeries().model_dump()
            for ds, param in product(
                ["current", "voltage", "time"], ["gain", "offset"]
            ):
                cal_dict[ds][param] = self.h5file["data"][ds].attrs[param]
            self._cal = CalibrationSeries(**cal_dict)

        self._refresh_file_stats()

        if file_path is not None:
            # file opened by this reader
            self._logger.info(
                "Reading data from '%s'\n"
                "\t- runtime %.1f s\n"
                "\t- mode = %s\n"
                "\t- window_size = %d\n"
                "\t- size = %.3f MiB\n"
                "\t- rate = %.0f KiB/s",
                self.file_path,
                self.runtime_s,
                self.get_mode(),
                self.get_window_samples(),
                self.file_size / 2**20,
                self.data_rate / 2**10,
            )

    def __enter__(self):
        return self

    def __exit__(self, *exc):  # type: ignore
        if self._reader_opened:
            self.h5file.close()

    def __repr__(self):
        return yaml.safe_dump(
            self.get_metadata(minimal=True), default_flow_style=False, sort_keys=False
        )

    def _refresh_file_stats(self) -> None:
        """update internal states, helpful after resampling or other changes in data-group"""
        self.h5file.flush()
        if (self.ds_time.shape[0] > 1) and (self.ds_time[1] != self.ds_time[0]):
            self.sample_interval_s = self._cal.time.raw_to_si(
                self.ds_time[1] - self.ds_time[0]
            )
            self.sample_interval_ns = int(10**9 * self.sample_interval_s)
            self.samplerate_sps = max(int(10**9 // self.sample_interval_ns), 1)
        self.runtime_s = round(self.ds_time.shape[0] / self.samplerate_sps, 1)
        if isinstance(self.file_path, Path):
            self.file_size = self.file_path.stat().st_size
        else:
            self.file_size = 0
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def read_buffers(
        self, start_n: int = 0, end_n: Optional[int] = None, is_raw: bool = False
    ) -> Generator[tuple, None, None]:
        """Generator that reads the specified range of buffers from the hdf5 file.
        can be configured on first call
        TODO: reconstruct - start/end mark samples and
              each call can request a certain number of samples

        Args:
            :param start_n: (int) Index of first buffer to be read
            :param end_n: (int) Index of last buffer to be read
            :param is_raw: (bool) output original data, not transformed to SI-Units
        Yields:
            Buffers between start and end (tuple with time, voltage, current)
        """
        if end_n is None:
            end_n = int(self.ds_time.shape[0] // self.samples_per_buffer)
        self._logger.debug(
            "Reading blocks from %d to %d from source-file", start_n, end_n
        )
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
                    self._cal.time.raw_to_si(self.ds_time[idx_start:idx_end]),
                    self._cal.voltage.raw_to_si(self.ds_voltage[idx_start:idx_end]),
                    self._cal.current.raw_to_si(self.ds_current[idx_start:idx_end]),
                )

    def get_calibration_data(self) -> CalibrationSeries:
        """Reads calibration-data from hdf5 file.

        :return: Calibration data as CalibrationSeries object
        """
        return self._cal

    def get_window_samples(self) -> int:
        if "window_samples" in self.h5file["data"].attrs:
            return int(self.h5file["data"].attrs["window_samples"])
        return 0

    def get_mode(self) -> str:
        if "mode" in self.h5file.attrs:
            return self.h5file.attrs["mode"]
        return ""

    def get_config(self) -> Dict:
        if "config" in self.h5file["data"].attrs:
            return yaml.safe_load(self.h5file["data"].attrs["config"])
        return {}

    def get_hostname(self) -> str:
        if "hostname" in self.h5file.attrs:
            return self.h5file.attrs["hostname"]
        return "unknown"

    def get_datatype(self) -> Optional[EnergyDType]:
        try:
            if "datatype" in self.h5file["data"].attrs:
                return EnergyDType[self.h5file["data"].attrs["datatype"]]
            return None
        except KeyError:
            return None

    def get_hrv_config(self) -> dict:
        """essential info for harvester
        :return: config-dict directly for vHarvester to be used during emulation
        """
        return {
            "datatype": self.get_datatype(),
            "window_samples": self.get_window_samples(),
        }

    def is_valid(self) -> bool:
        """checks file for plausibility

        :return: state of validity
        """
        # hard criteria
        if "data" not in self.h5file.keys():
            self._logger.error("root data-group not found (@Validator)")
            return False
        for attr in ["mode"]:
            if attr not in self.h5file.attrs.keys():
                self._logger.error(
                    "attribute '%s' not found in file (@Validator)", attr
                )
                return False
            if self.h5file.attrs["mode"] not in self.mode_dtype_dict:
                self._logger.error("unsupported mode '%s' (@Validator)", attr)
                return False
        for attr in ["window_samples", "datatype"]:
            if attr not in self.h5file["data"].attrs.keys():
                self._logger.error(
                    "attribute '%s' not found in data-group (@Validator)", attr
                )
                return False
        for dset in ["time", "current", "voltage"]:
            if dset not in self.h5file["data"].keys():
                self._logger.error("dataset '%s' not found (@Validator)", dset)
                return False
            for attr in ["gain", "offset"]:
                if attr not in self.h5file["data"][dset].attrs.keys():
                    self._logger.error(
                        "attribute '%s' not found in dataset '%s' (@Validator)",
                        attr,
                        dset,
                    )
                    return False
        if self.get_datatype() not in self.mode_dtype_dict[self.get_mode()]:
            self._logger.error(
                "unsupported type '%s' for mode '%s' (@Validator)",
                self.get_datatype(),
                self.get_mode(),
            )
            return False

        if self.get_datatype() == EnergyDType.ivcurve and self.get_window_samples() < 1:
            self._logger.error(
                "window size / samples is < 1 "
                "-> invalid for ivcurve-datatype (@Validator)"
            )
            return False

        # soft-criteria:
        if self.get_datatype() != EnergyDType.ivcurve and self.get_window_samples() > 0:
            self._logger.warning(
                "window size / samples is > 0 despite "
                "not using the ivcurve-datatype (@Validator)"
            )
        # same length of datasets:
        ds_time_size = self.h5file["data"]["time"].shape[0]
        for dset in ["current", "voltage"]:
            ds_size = self.h5file["data"][dset].shape[0]
            if ds_time_size != ds_size:
                self._logger.warning(
                    "dataset '%s' has different size (=%d), "
                    "compared to time-ds (=%d) (@Validator)",
                    dset,
                    ds_size,
                    ds_time_size,
                )
        # dataset-length should be multiple of buffersize
        remaining_size = ds_time_size % self.samples_per_buffer
        if remaining_size != 0:
            self._logger.warning(
                "datasets are not aligned with buffer-size (@Validator)"
            )
        # check compression
        for dset in ["time", "current", "voltage"]:
            comp = self.h5file["data"][dset].compression
            opts = self.h5file["data"][dset].compression_opts
            if comp not in [None, "gzip", "lzf"]:
                self._logger.warning(
                    "unsupported compression found (%s != None, lzf, gzip) (@Validator)",
                    comp,
                )
            if (comp == "gzip") and (opts is not None) and (int(opts) > 1):
                self._logger.warning(
                    "gzip compression is too high (%d > 1) for BBone (@Validator)", opts
                )
        # host-name
        if self.get_hostname() == "unknown":
            self._logger.warning("Hostname was not set (@Validator)")
        return True

    def __getitem__(self, key: str):
        """returns attribute or (if none found) a handle for a group or dataset (if found)

        :param key: attribute, group, dataset
        :return: value of that key, or handle of object
        """
        if key in self.h5file.attrs:
            return self.h5file.attrs.__getitem__(key)
        if key in self.h5file:
            return self.h5file.__getitem__(key)
        raise KeyError

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

        def _calc_energy(idx_start: int) -> float:
            idx_stop = min(idx_start + self.max_elements, self.ds_time.shape[0])
            vol_v = self._cal.voltage.raw_to_si(self.ds_voltage[idx_start:idx_stop])
            cur_a = self._cal.current.raw_to_si(self.ds_current[idx_start:idx_stop])
            return (vol_v[:] * cur_a[:]).sum() * self.sample_interval_s

        energy_ws = [_calc_energy(i) for i in job_iter]
        return float(sum(energy_ws))

    def _dset_statistics(
        self, dset: h5py.Dataset, cal: Optional[CalibrationPair] = None
    ) -> Dict[str, float]:
        """some basic stats for a provided dataset
        :param dset: dataset to evaluate
        :param cal: calibration (if wanted)
        :return: dict with entries for mean, min, max, std
        """
        si_converted = True
        if not isinstance(cal, CalibrationPair):
            if "gain" in dset.attrs and "offset" in dset.attrs:
                cal = CalibrationPair(
                    gain=dset.attrs["gain"], offset=dset.attrs["offset"]
                )
            else:
                cal = CalibrationPair(gain=1)
                si_converted = False
        iterations = math.ceil(dset.shape[0] / self.max_elements)
        job_iter = trange(
            0,
            dset.shape[0],
            self.max_elements,
            desc=f"{dset.name}-stats",
            leave=False,
            disable=iterations < 8,
        )

        def _calc_statistics(data: np.ndarray) -> list:
            return [np.mean(data), np.min(data), np.max(data), np.std(data)]

        stats_list = [
            _calc_statistics(cal.raw_to_si(dset[i : i + self.max_elements]))
            for i in job_iter
        ]
        if len(stats_list) < 1:
            return {}
        stats_nd = np.stack(stats_list)
        stats: Dict[str, float] = {
            # TODO: wrong calculation for ndim-datasets with n>1
            "mean": float(stats_nd[:, 0].mean()),
            "min": float(stats_nd[:, 1].min()),
            "max": float(stats_nd[:, 2].max()),
            "std": float(stats_nd[:, 3].mean()),  # TODO: sooo wrong :)
            "si_converted": si_converted,
        }
        return stats

    def data_timediffs(self) -> List[float]:
        """calculate list of (unique) time-deltas between buffers [s]
            -> optimized version that only looks at the start of each buffer

        :return: list of (unique) time-deltas between buffers [s]
        """
        iterations = math.ceil(self.ds_time.shape[0] / self.max_elements)
        job_iter = trange(
            0,
            self.h5file["data"]["time"].shape[0],
            self.max_elements,
            desc="timediff",
            leave=False,
            disable=iterations < 8,
        )

        def calc_timediffs(idx_start: int) -> list:
            ds_time = self.ds_time[
                idx_start : (idx_start + self.max_elements) : self.samples_per_buffer
            ]
            diffs_np = np.unique(ds_time[1:] - ds_time[0:-1], return_counts=False)
            return list(np.array(diffs_np))

        diffs_ll = [calc_timediffs(i) for i in job_iter]
        diffs = {
            round(self._cal.time.raw_to_si(j) / self.samples_per_buffer, 6)
            for i in diffs_ll
            for j in i
        }
        return list(diffs)

    def check_timediffs(self) -> bool:
        """validate equal time-deltas
        -> unexpected time-jumps hint at a corrupted file or faulty measurement

        :return: True if OK
        """
        diffs = self.data_timediffs()
        if len(diffs) > 1:
            self._logger.warning(
                "Time-jumps detected -> expected equal steps, but got: %s s", diffs
            )
        return (len(diffs) <= 1) and diffs[0] == round(0.1 / self.samples_per_buffer, 6)

    def get_metadata(
        self, node: Union[h5py.Dataset, h5py.Group, None] = None, minimal: bool = False
    ) -> Dict[str, dict]:
        """recursive FN to capture the structure of the file
        TODO: port to BaseReader (.data_dimediffs(), _dset_statistics())
        :param node: starting node, leave free to go through whole file
        :param minimal: just provide a bare tree (much faster)
        :return: structure of that node with everything inside it
        """
        if node is None:
            self._refresh_file_stats()
            return self.get_metadata(self.h5file, minimal=minimal)

        metadata: Dict[str, dict] = {}
        if isinstance(node, h5py.Dataset) and not minimal:
            metadata["_dataset_info"] = {
                "datatype": str(node.dtype),
                "shape": str(node.shape),
                "chunks": str(node.chunks),
                "compression": str(node.compression),
                "compression_opts": str(node.compression_opts),
            }
            if node.name == "/data/time":
                metadata["_dataset_info"]["time_diffs_s"] = self.data_timediffs()
                # TODO: already convert to str to calm the typechecker?
                #  or construct a pydantic-class
            elif "int" in str(node.dtype):
                metadata["_dataset_info"]["statistics"] = self._dset_statistics(node)
                # TODO: put this into metadata["_dataset_statistics"] ??
        for attr in node.attrs.keys():
            attr_value = node.attrs[attr]
            if isinstance(attr_value, str):
                with contextlib.suppress(yaml.YAMLError):
                    attr_value = yaml.safe_load(attr_value)
            elif "int" in str(type(attr_value)):
                # TODO: why not isinstance? can it be List[int] other complex type?
                attr_value = int(attr_value)
            else:
                attr_value = float(attr_value)
            metadata[attr] = attr_value
        if isinstance(node, h5py.Group):
            if node.name == "/data" and not minimal:
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

    def save_metadata(self, node: Union[h5py.Dataset, h5py.Group, None] = None) -> dict:
        """get structure of file and dump content to yaml-file with same name as original

        :param node: starting node, leave free to go through whole file
        :return: structure of that node with everything inside it
        """
        if isinstance(self.file_path, Path):
            yaml_path = Path(self.file_path).resolve().with_suffix(".yaml")
            if yaml_path.exists():
                self._logger.info("%s already exists, will skip", yaml_path)
                return {}
            metadata = self.get_metadata(
                node
            )  # {"h5root": self.get_metadata(self.h5file)}
            with open(yaml_path, "w", encoding="utf-8-sig") as yfd:
                yaml.safe_dump(metadata, yfd, default_flow_style=False, sort_keys=False)
        else:
            metadata = {}
        return metadata
