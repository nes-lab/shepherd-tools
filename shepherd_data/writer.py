"""
Writer that inherits from Reader-Baseclass
"""
import math
from typing import NoReturn, Union, Dict
import logging

import numpy as np
from pathlib import Path
import h5py
from itertools import product
import yaml

from .reader import Reader


def unique_path(base_path: Union[str, Path], suffix: str) -> Path:
    """finds an unused filename in case it already exists

    :param base_path: file-path to test
    :param suffix: file-suffix
    :return: new non-existing path
    """
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
    mode_default: str = "harvester"
    datatype_default: str = "ivsample"
    cal_default: dict[str, dict] = general_calibration

    chunk_shape: tuple = (Reader.samples_per_buffer,)

    logger: logging.Logger = logging.getLogger("SHPData.Writer")

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

        if self._modify or not file_path.exists():
            self.file_path = file_path
            self.logger.info("Storing data to   '%s'", self.file_path)
        else:
            base_dir = file_path.resolve().parents[0]
            self.file_path = unique_path(base_dir / file_path.stem, file_path.suffix)
            self.logger.warning(
                "File %s already exists -> " "storing under %s instead",
                file_path,
                self.file_path.name,
            )

        if not isinstance(mode, (str, type(None))):
            raise TypeError(f"can not handle type '{type(mode)}' for mode")
        if isinstance(mode, str) and mode not in self.mode_type_dict:
            raise ValueError(f"can not handle mode '{mode}'")

        if not isinstance(datatype, (str, type(None))):
            raise TypeError(f"can not handle type '{type(datatype)}' for datatype")
        if (
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
            self.data_grp["time"].attrs["unit"] = "ns"
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
            self.logger.error("datatype invalid? '%s' not written", self.datatype)

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
            "closing hdf5 file, %s s iv-data, size = %s MiB, rate = %s KiB/s",
            self.runtime_s,
            round(self.file_size / 2**20, 3),
            round(self.data_rate / 2**10),
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
            self.logger.error("timestamp-data was not usable")
            return

        len_old = self.ds_time.shape[0]

        # resize dataset
        self.ds_time.resize((len_old + len_new,))
        self.ds_voltage.resize((len_old + len_new,))
        self.ds_current.resize((len_old + len_new,))

        # append new data
        self.ds_time[len_old : len_old + len_new] = timestamp_ns[:len_new]
        self.ds_voltage[len_old : len_old + len_new] = voltage[:len_new]
        self.ds_current[len_old: len_old + len_new] = current[:len_new]

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
                self.logger.debug("skipped alignment due to altered samplerate")
                return
            self.logger.info(
                "aligning with buffer-size, discarding last %s entries",
                self.ds_time.size - size_new,
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
