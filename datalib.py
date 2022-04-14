# -*- coding: utf-8 -*-

"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import logging
from typing import NoReturn, Union, Dict

import numpy as np
from pathlib import Path
import h5py
from itertools import product
import yaml

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
}


class ShepherdReader(object):
    """ Sequentially Reads data from HDF5 file.

    Args:
        file_path (Path): Path of hdf5 file containing IV data
    """

    samples_per_buffer: int = 10_000
    samplerate_sps: int = 100_000
    sample_interval_ns = int(10 ** 9 // samplerate_sps)

    def __init__(self, file_path: Union[Path, None], verbose: bool = True):
        self._skip_read = file_path is None  # for access by writer-class
        if not self._skip_read:
            self.file_path = file_path
        logger.setLevel(logging.INFO if verbose else logging.WARNING)

    def __enter__(self):
        if not self._skip_read:
            self._h5file = h5py.File(self.file_path, "r")

        if self.is_valid():
            logger.info("[ShpReader] File was valid and will be available now")
        else:
            raise ValueError("[ShpReader] File was faulty, will not Open")

        self.ds_time = self._h5file["data"]["time"]
        self.ds_voltage = self._h5file["data"]["voltage"]
        self.ds_current = self._h5file["data"]["current"]
        self.cal = {
            "voltage": {"gain": self.ds_voltage.attrs["gain"], "offset": self.ds_voltage.attrs["offset"]},
            "current": {"gain": self.ds_current.attrs["gain"], "offset": self.ds_current.attrs["offset"]},
        }

        if not self._skip_read:
            runtime = round(self.ds_time.shape[0] / self.samplerate_sps, 1)
            logger.info(
                f"[ShpReader] Reading data from '{self.file_path}', "
                f"contains {runtime} s, "
                f"mode = {self.get_mode()}, "
                f"window_size = {self.get_window_samples()}")
        return self

    def __exit__(self, *exc):
        if not self._skip_read:
            self._h5file.close()

    def read_buffers_raw(self, start: int = 0, end: int = None):
        """Reads the specified range of buffers from the hdf5 file.

        Args:
            :param start: (int): Index of first buffer to be read
            :param end: (int): Index of last buffer to be read
        Yields:
            Buffers between start and end
        """
        if end is None:
            end = int(self._h5file["data"]["time"].shape[0] // self.samples_per_buffer)
        logger.debug(f"[ShpReader] Reading blocks from {start} to {end} from source-file")

        for i in range(start, end):
            idx_start = i * self.samples_per_buffer
            idx_end = idx_start + self.samples_per_buffer
            yield (self.ds_time[idx_start:idx_end],
                   self.ds_voltage[idx_start:idx_end],
                   self.ds_current[idx_start:idx_end])

    def read_buffers_si(self, start: int = 0, end: int = None, verbose: bool = False):
        # TODO
        pass

    def __getitem__(self, key):
        return self._h5file.attrs.__getitem__(key)

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

    def is_valid(self) -> bool:
        # hard criteria
        if "data" not in self._h5file.keys():
            logger.error(f"[ShpReader|validator] root data-group not found")
            return False
        for attr in ["mode"]:
            if attr not in self._h5file.attrs.keys():
                logger.error(f"[ShpReader|validator] attribute '{attr}' in file not found")
                return False
        for attr in ["window_samples"]:
            if attr not in self._h5file["data"].attrs.keys():
                logger.error(f"[ShpReader|validator] attribute '{attr}' in data-group not found")
                return False
        for ds in ["time", "current", "voltage"]:
            if ds not in self._h5file["data"].keys():
                logger.error(f"[ShpReader|validator] dataset '{ds}' not found")
                return False
        for ds, attr in product(["current", "voltage"], ["gain", "offset"]):
            if attr not in self._h5file["data"][ds].attrs.keys():
                logger.error(f"[ShpReader|validator] attribute '{attr}' in dataset '{ds}' not found")
                return False

        # soft-criteria:
        # same length of datasets:
        ds_time_size = self._h5file["data"]["time"].shape[0]
        for ds in ["current", "voltage"]:
            ds_size = self._h5file["data"][ds].shape[0]
            if ds_time_size != ds_size:
                logger.error(f"[ShpReader|validator] dataset '{ds}' has different size (={ds_size}), "
                             f"compared to time-ds (={ds_time_size})")
        # dataset-length should be multiple of buffersize
        remaining_size = ds_time_size % self.samples_per_buffer
        if remaining_size != 0:
            logger.error(f"[ShpReader|validator] datasets are not aligned with buffer-size")
        # check compression
        for ds in ["time", "current", "voltage"]:
            comp = self._h5file["data"][ds].compression
            opts = self._h5file["data"][ds].compression_opts
            if comp not in [None, "gzip", "lzf"]:
                logger.error(f"[ShpReader|validator] unsupported compression found ({comp} != None, lzf, gzip)")
            if (comp == "gzip") and (opts is not None) and (int(opts) > 1):
                logger.error(f"[ShpReader|validator] gzip compression is too high ({opts} > 1) for BBone")

        return True

    def get_metadata(self, node=None) -> dict:
        """ recursive FN to capture the structure of the file
        :param node: starting node, leave free to go through whole file
        :return: structure of that node everything inside it
        """
        # recursive...
        if node is None:
            return {"h5root": self.get_metadata(self._h5file)}

        metadata = {}
        if isinstance(node, h5py.Dataset):
            metadata["_dataset_info"] = {
                "dtype": str(node.dtype),
                "shape": str(node.shape),
                "chunks": str(node.chunks),
                "compression": str(node.compression),
                "compression_opts": str(node.compression_opts),
            }
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
            for item in node.keys():
                metadata[item] = self.get_metadata(node[item])

        return metadata

    def save_metadata(self, node=None) -> NoReturn:
        """ get structure of file and dump content to yaml-file with same name as original
        :param node: starting node, leave free to go through whole file
        """
        metadata = self.get_metadata(node)
        file_path = Path(self.file_path).absolute()
        with open(file_path.with_suffix(".yml"), "w") as fd:
            yaml.safe_dump(metadata, fd, default_flow_style=False, sort_keys=False)

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
    comp_default = None
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

        file_path = Path(file_path)
        self._modify = modify_existing

        if self._modify or not file_path.exists():
            self.file_path = file_path
            logger.info(f"[ShpWriter] Storing data to   '{self.file_path}'")
        else:
            base_dir = file_path.resolve().parents[0]
            self.file_path = unique_path(
                base_dir / file_path.stem, file_path.suffix
            )
            logger.warning(
                f"[ShpWriter] File {file_path} already exists.. "
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

    def embed_config(self, data: dict) -> NoReturn:
        """
        Important Step to get a self-describing Output-File
        Note: the size of window_samples-attribute in harvest-data indicates ivcurves as input -> emulator uses virtual-harvester

        :param data: from virtual harvester or converter / source
        :return: None
        """
        self.data_grp.attrs["config"] = yaml.dump(data, default_flow_style=False)
        if "window_samples" in data:
            self.data_grp.attrs["window_samples"] = data["window_samples"]

    def __exit__(self, *exc):
        runtime = round(self.data_grp['time'].shape[0] / self.samplerate_sps, 1)
        logger.info(f"[ShpWriter] flushing hdf5 file, {runtime} s iv-data")
        self._h5file.flush()
        logger.info("[ShpWriter] closing  hdf5 file")
        self._h5file.close()

    def append_iv_data_raw(self, timestamp_ns, voltage: np.ndarray, current: np.ndarray) -> NoReturn:
        """Writes data to file.

        """
        length_data_new = min(voltage.size, current.size)

        if isinstance(timestamp_ns, float):
            timestamp_ns = int(timestamp_ns)
        if isinstance(timestamp_ns, int):
            time_series_ns = self.sample_interval_ns * np.arange(length_data_new).astype("u8")
            timestamp_ns = timestamp_ns + time_series_ns
        if isinstance(timestamp_ns, np.ndarray):
            length_data_new = min(length_data_new, timestamp_ns.size)
        else:
            logger.error("[ShpWriter] timestamp-data was not usable")
            return

        length_data_old = self.data_grp["time"].shape[0]

        # resize dataset
        self.data_grp["time"].resize((length_data_old + length_data_new,))
        self.data_grp["voltage"].resize((length_data_old + length_data_new,))
        self.data_grp["current"].resize((length_data_old + length_data_new,))

        # append new data
        self.data_grp["time"][length_data_old:length_data_new] = timestamp_ns
        self.data_grp["voltage"][length_data_old:length_data_new] = voltage[:length_data_new]
        self.data_grp["current"][length_data_old:length_data_new] = current[:length_data_new]

    def append_iv_data_si(self, timestamp, voltage: np.ndarray, current: np.array) -> NoReturn:
        """ Writes data to file, but converts it to raw-data first

        Args:
            timestamp: python timestamp (time.time()) in seconds (si-unit)
            voltage: ndarray in si-units
            current: ndarray in si-units

        Returns:

        """
        # SI-value [SI-Unit] = raw-value * gain + offset, # TODO: inherit convert-fn from reader
        timestamp = timestamp * 10**9
        voltage = (voltage - self.cal["voltage"]["offset"]) / self.cal["voltage"]["gain"]
        current = (current - self.cal["current"]["offset"]) / self.cal["current"]["gain"]
        self.append_iv_data_raw(timestamp, voltage, current)

    def __setitem__(self, key, item):
        """Offer a convenient interface to store any relevant key-value data (attribute) of H5-file-structure"""
        return self._h5file.attrs.__setitem__(key, item)
