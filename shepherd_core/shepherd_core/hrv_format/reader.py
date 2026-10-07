"""Reader-Baseclass for an optimized testbed-harvesting-format."""

from __future__ import annotations

import errno
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import h5py
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.config import core_config
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.content.enum_datatypes import EnergyDType

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Sequence
    from types import TracebackType


class Reader:
    """Sequentially Reads harvesting-data from HDF5 file.

    This is a special optimized format for the testbed
    that is directly precomputing the memory-layout between userspace & PRU.

    Args:
    ----
        file_path: Path of hdf5 file containing shepherd data with iv-samples, iv-curves or isc&voc
        verbose: more debug-info during usage, 'None' skips the setter

    """

    CHUNK_SAMPLES_N: int = 10_000

    HRV_DTYPES: Sequence[EnergyDType] = (
        EnergyDType.ivsample,
        EnergyDType.ivcurve,
        EnergyDType.isc_voc,
    )

    @validate_call
    def __init__(
        self,
        file_path: Path,
        *,
        verbose: bool = True,
    ) -> None:
        self.file_path: Path = file_path.resolve()

        if not hasattr(self, "_logger"):
            self._logger: logging.Logger = logging.getLogger("SHPCore.HrvReader")
        if verbose is not None:
            self._logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        # init stats
        self.runtime_s: float = 0
        self.samples_n: int = 0
        self.chunks_n: int = 0
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

            try:
                self.h5file = h5py.File(self.file_path, "r")  # = readonly
                self._reader_opened = True
            except OSError as xcp:
                msg = f"Unable to open HDF5-File '{self.file_path.name}'"
                raise TypeError(msg) from xcp

            if self.is_valid():
                self._logger.debug("File is available now")
            else:
                self._logger.error(
                    "[FileValidation] File is faulty! "
                    "Will try to open but there might be dragons, for '%s'",
                    self.file_path.name,
                )

        if not isinstance(self.h5file, h5py.File):
            msg = (f"Type of opened file is not h5py.File, for {self.file_path.name}",)
            raise TypeError(msg)

        self.ds: h5py.Dataset = self.h5file["harvest"]["iv"]

        # retrieve cal-data
        if not hasattr(self, "_cal"):
            self._cal = CalibrationSeries(
                # sheep skips scaling if cal is ideal (applied here)
                voltage=CalibrationPair(gain=1e-6, offset=0),
                current=CalibrationPair(gain=1e-9, offset=0),
            )

        self._refresh_file_stats()

        if file_path is not None:
            # file opened by this reader
            self._logger.debug(
                "Reading data from '%s'\n"
                "\t- runtime %.1f s\n"
                "\t- mode = %s\n"
                "\t- window_size = %d\n"
                "\t- size = %.3f MiB\n"
                "\t- rate = %.0f KiB/s",
                self.file_path.name,
                self.runtime_s,
                self.get_mode(),
                self.get_window_samples(),
                self.file_size / 2**20,
                self.data_rate / 2**10,
            )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        typ: type[BaseException] | None = None,
        exc: BaseException | None = None,
        tb: TracebackType | None = None,
        extra_arg: int = 0,
    ) -> None:
        if self._reader_opened:
            self.h5file.close()

    def _refresh_file_stats(self) -> None:
        """Update internal states, helpful after resampling or other changes in data-group."""
        self.h5file.flush()
        self.samples_n = self.ds.shape[0]
        self.runtime_s = round(self.samples_n / core_config.SAMPLERATE_SPS, 1)
        self.chunks_n = int(self.samples_n // self.CHUNK_SAMPLES_N)
        if isinstance(self.file_path, Path):
            self.file_size = self.file_path.stat().st_size
        else:
            self.file_size = 0
        self.data_rate = self.file_size / self.runtime_s if self.runtime_s > 0 else 0

    def read(
        self,
        start_n: int = 0,
        end_n: int | None = None,
        n_samples_per_chunk: int | None = None,
        *,
        is_raw: bool = True,
        omit_timestamps: bool = True,
    ) -> Generator[tuple, None, None]:
        """Read the specified range of chunks from the hdf5 file.

        Generator - can be configured on first call

        Args:
            start_n: (int) Index of first chunk to be read
            end_n: (int) Index of last chunk to be read
            n_samples_per_chunk: (int) allows changing
            is_raw: (bool) output original data, not transformed to SI-Units
            omit_timestamps: (bool) optimize reading if timestamp is never used

        Yields:
            chunks between start and end (tuple with time, voltage, current)

        """
        if not is_raw:
            raise ValueError("HrvReader is optimized for (and only capable of) raw data-output")
        if not omit_timestamps:
            raise ValueError("HrvFormat does not contain timestamps")
        if n_samples_per_chunk is None:
            n_samples_per_chunk = self.CHUNK_SAMPLES_N
        end_max = int(self.samples_n // n_samples_per_chunk)
        end_n = end_max if end_n is None else min(end_n, end_max)
        self._logger.debug("Reading chunk %d to %d from source-file", start_n, end_n)

        for i in range(start_n, end_n):
            idx_start = i * n_samples_per_chunk
            idx_end = idx_start + n_samples_per_chunk
            yield self.ds[idx_start:idx_end]

    def get_calibration_data(self) -> CalibrationSeries:
        """Read calibration-data from hdf5 file.

        :return: Calibration data as CalibrationSeries object
        """
        return self._cal

    def get_window_samples(self) -> int:
        if "window_samples" in self.h5file["harvest"].attrs:
            return int(self.h5file["harvest"].attrs["window_samples"])
        return 0

    def get_mode(self) -> str:
        if "mode" in self.h5file.attrs:
            return self.h5file.attrs["mode"]
        return ""

    def get_datatype(self) -> EnergyDType | None:
        try:
            if "datatype" in self.h5file["harvest"].attrs:
                return EnergyDType[self.h5file["harvest"].attrs["datatype"]]
        except KeyError:
            return None
        except ValueError:
            return None
        else:
            return None

    def is_valid(self) -> bool:
        """Check file for plausibility, validity / correctness.

        :return: state of validity
        """
        # hard criteria
        if "harvest" not in self.h5file:
            self._logger.error(
                "[FileValidation] root data-group not found in '%s'",
                self.file_path.name,
            )
            return False
        for attr in ["mode"]:
            if attr not in self.h5file.attrs:
                self._logger.error(
                    "[FileValidation] attribute '%s' not found in '%s'",
                    attr,
                    self.file_path.name,
                )
                return False
            if self.h5file.attrs["mode"] != "harvester":
                self._logger.error(
                    "[FileValidation] unsupported mode '%s' in '%s'",
                    attr,
                    self.file_path.name,
                )
                return False
        for attr in ["window_samples", "datatype"]:
            if attr not in self.h5file["harvest"].attrs:
                self._logger.error(
                    "[FileValidationError] attribute '%s' not found in data-group in '%s'",
                    attr,
                    self.file_path.name,
                )
                return False
        for dset in ["iv"]:
            if dset not in self.h5file["harvest"]:
                self._logger.error(
                    "[FileValidation] dataset '%s' not found in '%s'",
                    dset,
                    self.file_path.name,
                )
                return False
        if self.get_datatype() not in self.HRV_DTYPES:
            self._logger.error(
                "[FileValidation] unsupported type '%s' for mode '%s'  in '%s'",
                self.get_datatype(),
                self.get_mode(),
                self.file_path.name,
            )
            return False

        if self.get_datatype() == EnergyDType.ivcurve and self.get_window_samples() < 1:
            self._logger.error(
                "[FileValidation] window size / samples is < 1 "
                "-> invalid for ivcurve-datatype, in '%s'",
                self.file_path.name,
            )
            return False

        # soft-criteria:
        if self.get_datatype() != EnergyDType.ivcurve and self.get_window_samples() > 0:
            self._logger.warning(
                "[FileValidation] window size / samples is > 0 despite "
                "not using the ivcurve-datatype, in '%s'",
                self.file_path.name,
            )
        # same length of datasets:
        samples_n = self.h5file["harvest"]["iv"].shape[0]

        # dataset-length should be multiple of chunk-size
        remaining_size = samples_n % self.CHUNK_SAMPLES_N
        if remaining_size != 0:
            self._logger.warning(
                "[FileValidation] dataset is not aligned with chunk-size in '%s'",
                self.file_path.name,
            )
        # check compression
        for dset in ["iv"]:
            comp = self.h5file["harvest"][dset].compression
            opts = self.h5file["harvest"][dset].compression_opts
            if comp != "lzf":
                self._logger.warning(
                    "[FileValidation] unsupported compression found (%s != lzf) in '%s'",
                    comp,
                    self.file_path.name,
                )
            if (comp == "gzip") and (opts is not None) and (int(opts) > 7):
                self._logger.warning(
                    "[FileValidation] gzip compression is too high (%d > 1) for BBone in '%s'",
                    opts,
                    self.file_path.name,
                )
        return True

    def __getitem__(self, key: str) -> Any:
        """Query attribute or (if none found) a handle for a group or dataset (if found).

        :param key: attribute, group, dataset
        :return: value of that key, or handle of object
        """
        if key in self.h5file.attrs:
            return self.h5file.attrs.__getitem__(key)
        if key in self.h5file:
            return self.h5file.__getitem__(key)
        raise KeyError
