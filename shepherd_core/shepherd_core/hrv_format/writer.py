"""Writer for an optimized testbed-harvesting-format."""

import logging
import math
from pathlib import Path
from types import TracebackType
from typing import Any

import h5py
import numpy as np
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.data_models.content.enum_datatypes import Compression
from shepherd_core.data_models.content.enum_datatypes import EnergyDType
from shepherd_core.data_models.content.enum_datatypes import compression_dict

from .reader import Reader


class Writer(Reader):
    """Stores data for Shepherd-testbed in HDF5 format.

    This is a special optimized format for the testbed
    that is directly precomputing the memory-layout between userspace & PRU.

    Args:
    ----
        file_path: (Path) Name of the HDF5 file that data will be written to
        datatype: (str) choose type: ivsample (most common), ivcurve or isc_voc
        window_samples: (int) windows size for the datatype ivcurve
        verbose: (bool) provides more debug-info

    """

    DATATYPE_DEFAULT: EnergyDType = EnergyDType.ivsample

    _CHUNK_SHAPE: tuple = (Reader.CHUNK_SAMPLES_N, 2)

    @validate_call
    def __init__(
        self,
        file_path: Path,
        datatype: str | EnergyDType | None = None,
        window_samples: int | None = None,
        *,
        force_overwrite: bool = False,
        verbose: bool = True,
    ) -> None:
        self._modify: bool = False  # keep it simple

        self._compression = compression_dict[Compression.lzf]

        if not hasattr(self, "_logger"):
            self._logger: logging.Logger = logging.getLogger("SHPCore.HrvWriter")
            self._logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        # -> logger gets configured in reader()

        if file_path.suffix.lower() not in Writer.SUFFIX_VALID:
            msg = (
                f"Filename for recording ({file_path.name}) "
                f"must have a valid suffix ({Writer.SUFFIX_VALID})"
            )
            raise ValueError(msg)
        if self._modify or force_overwrite or not file_path.exists():
            file_path = file_path.resolve()
            self._logger.debug("Storing data to   '%s'", file_path)
        elif file_path.exists() and not file_path.is_file():
            msg = f"Path is not a file ({file_path})"
            raise TypeError(msg)
        else:
            raise TypeError(
                "File '%s' already exists! please select another or enable 'force_overwrite'",
                file_path,
            )

        # open file
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)
        self.h5file = h5py.File(file_path, "w")
        # ⤷ write, truncate if exist
        self._create_skeleton()

        # Handle Mode
        self.h5file.attrs["mode"] = "harvester"

        # Handle Datatype
        if isinstance(datatype, str):
            datatype = EnergyDType[datatype]
        if isinstance(datatype, EnergyDType) and datatype not in self.HRV_DTYPES:
            msg = f"Can't handle value '{datatype}' of datatype (choose one of {self.HRV_DTYPES})"
            raise ValueError(msg)

        if isinstance(datatype, EnergyDType):
            self.h5file["harvest"].attrs["datatype"] = datatype.name
        if "datatype" not in self.h5file["harvest"].attrs:
            self.h5file["harvest"].attrs["datatype"] = self.DATATYPE_DEFAULT.name
        if self.get_datatype() not in self.HRV_DTYPES:
            msg = f"Can't handle datatype '{self.get_datatype()}' (choose one of {self.HRV_DTYPES})"
            raise ValueError(msg)

        # Handle Window_samples
        if window_samples is not None:
            self.h5file["harvest"].attrs["window_samples"] = window_samples
        if "window_samples" not in self.h5file["harvest"].attrs:
            self.h5file["harvest"].attrs["window_samples"] = 0

        if datatype == EnergyDType.ivcurve and self.get_window_samples() < 1:
            raise ValueError("Window Size argument needed for ivcurve-Datatype")

        # show key parameters for h5-performance
        settings = list(self.h5file.id.get_access_plist().get_cache())
        self._logger.debug("H5Py Cache_setting=%s (_mdc, _nslots, _nbytes, _w0)", settings)

        super().__init__(file_path=file_path, verbose=verbose)

    def __enter__(self) -> Self:
        self._test_endianness()
        super().__enter__()
        return self

    def __exit__(
        self,
        typ: type[BaseException] | None = None,
        exc: BaseException | None = None,
        tb: TracebackType | None = None,
        extra_arg: int = 0,
    ) -> None:
        self._align()
        self._refresh_file_stats()
        self._logger.debug(
            "closing hdf5 file, %.1f s iv-data, size = %.3f MiB, rate = %.0f KiB/s",
            self.runtime_s,
            self.file_size / 2**20,
            self.data_rate / 2**10,
        )
        self.is_valid()
        self.h5file.close()

    def __setitem__(self, key: str, item: Any) -> None:
        """Conveniently store relevant key-value data (attribute) in H5-structure."""
        self.h5file.attrs.__setitem__(key, item)

    def _create_skeleton(self) -> None:
        """Initialize the structure of the HDF5 file.

        HDF5 is hierarchically structured and before writing data, we have to
        set up this structure, i.e. creating the right groups with corresponding
        data types. We will store 3 types of data in a database: The
        actual IV samples recorded either from the harvester (during recording)
        or the target (during emulation). Any log messages, that can be used to
        store relevant events or tag some parts of the recorded data.

        """
        # Store voltage and current samples in the data group,
        # both are stored as 4 Byte unsigned int
        grp_data = self.h5file.create_group("harvest")
        # the size of window_samples-attribute in harvest-data indicates ivsurface / curves as input
        # -> emulator uses virtual-harvester, field will be adjusted by .embed_config()
        grp_data.attrs["window_samples"] = 0

        grp_data.create_dataset(
            "iv",
            (0, 2),
            dtype="u4",
            maxshape=(None, 2),
            chunks=self._CHUNK_SHAPE,
            compression=self._compression,
            shuffle=True,
        )
        grp_data["iv"].attrs["unit"] = "V;A"
        grp_data["iv"].attrs["description"] = "value_SI = value_raw * gain + offset"

    @staticmethod
    def _test_endianness() -> None:
        # test for endianness, has to be compatible with ARM32v7
        data = np.arange(4, dtype=np.uint32).reshape((-1, 2), order="C").tobytes()
        if data != b"\x00\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00":
            raise ValueError("Data not correct")

    def store_voltage_step(self, value_V: float) -> None:
        self.h5file.attrs["voltage_step_V"] = value_V

    def append_iv_data_raw(
        self,
        voltage: np.ndarray,
        current: np.ndarray,
    ) -> None:
        """Write raw data to database.

        Args:
        ----
            voltage: ndarray as raw unsigned integers
            current: ndarray as raw unsigned integers

        """
        len_new = min(len(voltage), len(current))
        len_old = len(self.ds)

        # interweave data (voltage | current in parallel)
        vi_data = np.empty((len_new, 2), dtype=voltage.dtype)
        vi_data[:, 0] = voltage[:len_new]
        vi_data[:, 1] = current[:len_new]

        # extend dataset
        self.ds.resize((len_old + len_new, 2))

        # append new data
        self.ds[len_old : len_old + len_new, :] = vi_data[:len_new, :]

    def append_iv_data_si(
        self,
        voltage: np.ndarray,
        current: np.ndarray,
    ) -> None:
        """Write data (provided in SI / physical unit) to file.

        This will convert it to raw-data first.

           SI-value [SI-Unit] = raw-value * gain + offset,

        Args:
        ----
            voltage: ndarray in physical-unit V
            current: ndarray in physical-unit A

        """
        voltage = self._cal.voltage.si_to_raw(voltage)
        current = self._cal.current.si_to_raw(current)
        self.append_iv_data_raw(voltage, current)

    def _align(self) -> None:
        """Align datasets with chunk-size of shepherd."""
        self._refresh_file_stats()
        chunks_n = len(self.ds) / self.CHUNK_SAMPLES_N
        size_new = int(math.floor(chunks_n) * self.CHUNK_SAMPLES_N)
        if size_new < len(self.ds):
            self._logger.info(
                "aligning with chunk-size, discarding last %d entries",
                len(self.ds) - size_new,
            )
            self.ds.resize((size_new, 2))
