"""Reader-Baseclass
"""
import math
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Union

import h5py
import numpy as np
from matplotlib import pyplot as plt
from tqdm import trange

from shepherd_core import Reader as CoreReader
from shepherd_core import local_tz
from shepherd_core.logger import logger

# import samplerate  # noqa: ERA001, TODO: just a test-fn for now


class Reader(CoreReader):
    """Sequentially Reads shepherd-data from HDF5 file.

    Args:
    ----
        file_path: Path of hdf5 file containing shepherd data with iv-samples, iv-curves or isc&voc
        verbose: more info during usage, 'None' skips the setter
    """

    def __init__(
        self,
        file_path: Optional[Path],
        *,
        verbose: Optional[bool] = True,
    ) -> None:
        super().__init__(file_path, verbose=verbose)

    def save_csv(self, h5_group: h5py.Group, separator: str = ";") -> int:
        """Extract numerical data via csv

        :param h5_group: can be external and should probably be downsampled
        :param separator: used between columns
        :return: number of processed entries
        """
        if h5_group["time"].shape[0] < 1:
            self._logger.warning("%s is empty, no csv generated", h5_group.name)
            return 0
        if not isinstance(self.file_path, Path):
            return 0
        csv_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.csv")
        if csv_path.exists():
            self._logger.info("File already exists, will skip '%s'", csv_path.name)
            return 0
        datasets = [key if isinstance(h5_group[key], h5py.Dataset) else [] for key in h5_group]
        datasets.remove("time")
        datasets = ["time", *datasets]
        separator = separator.strip().ljust(2)
        header = [h5_group[key].attrs["description"].replace(", ", separator) for key in datasets]
        header = separator.join(header)
        with csv_path.open("w", encoding="utf-8-sig") as csv_file:
            self._logger.info("CSV-Generator will save '%s' to '%s'", h5_group.name, csv_path.name)
            csv_file.write(header + "\n")
            for idx, time_ns in enumerate(h5_group["time"][:]):
                timestamp = datetime.fromtimestamp(time_ns / 1e9, tz=local_tz())
                csv_file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"))
                for key in datasets[1:]:
                    values = h5_group[key][idx]
                    if isinstance(values, np.ndarray):
                        values = separator.join([str(value) for value in values])
                    csv_file.write(f"{separator}{values}")
                csv_file.write("\n")
        return h5_group["time"][:].shape[0]

    def save_log(self, h5_group: h5py.Group, *, add_timestamp: bool = True) -> int:
        """Save dataset in group as log, optimal for logged dmesg and exceptions

        :param h5_group: can be external
        :param add_timestamp: can be external
        :return: number of processed entries
        """
        if h5_group["time"].shape[0] < 1:
            self._logger.warning("%s is empty, no log generated", h5_group.name)
            return 0
        if not isinstance(self.file_path, Path):
            return 0
        log_path = self.file_path.with_suffix(f".{h5_group.name.strip('/')}.log")
        if log_path.exists():
            self._logger.info("File already exists, will skip '%s'", log_path.name)
            return 0
        datasets = [key if isinstance(h5_group[key], h5py.Dataset) else [] for key in h5_group]
        datasets.remove("time")
        with log_path.open("w", encoding="utf-8-sig") as log_file:
            self._logger.info("Log-Generator will save '%s' to '%s'", h5_group.name, log_path.name)
            for idx, time_ns in enumerate(h5_group["time"][:]):
                if add_timestamp:
                    timestamp = datetime.fromtimestamp(time_ns / 1e9, local_tz())
                    # ⤷ TODO: these .fromtimestamp would benefit from included TZ
                    log_file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + ":")
                for key in datasets:
                    try:
                        message = str(h5_group[key][idx])
                    except OSError:
                        message = "[[[ extractor - faulty element ]]]"
                    log_file.write(f"\t{message}")
                log_file.write("\n")
        return h5_group["time"].shape[0]

    def warn_logs(
        self,
        group_name: str = "sheep",
        min_level: int = 30,
        limit: int = 10,
        *,
        show: bool = True,
    ) -> int:
        _count = self.count_errors_in_log(group_name, min_level)
        if _count < 1:
            return 0
        if not show:
            return _count
        self._logger.warning(
            "%s caught %d messages with level>=%d -> first %d are:",
            self.get_hostname(),
            _count,
            min_level,
            limit,
        )
        for idx, time_ns in enumerate(self.h5file[group_name]["time"][:]):
            _level = self.h5file[group_name]["level"][idx]
            if _level < min_level:
                continue
            _msg = self.h5file[group_name]["message"][idx]
            _timestamp = datetime.fromtimestamp(time_ns / 1e9, local_tz())
            if _level < 30:
                self._logger.info("    %s: %s", _timestamp, _msg)
            elif _level < 40:
                self._logger.warning("    %s: %s", _timestamp, _msg)
            else:
                self._logger.error("    %s: %s", _timestamp, _msg)
            limit -= 1
            if limit < 1:
                break
        return _count

    def downsample(
        self,
        data_src: h5py.Dataset,
        data_dst: Union[None, h5py.Dataset, np.ndarray],
        start_n: int = 0,
        end_n: Optional[int] = None,
        ds_factor: float = 5,
        *,
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
        from scipy import signal  # here due to massive delay

        if self.get_datatype() == "ivcurve":
            self._logger.warning("Downsampling-Function was not written for IVCurves")
        ds_factor = max(1, math.floor(ds_factor))

        if isinstance(end_n, (int, float)):
            _end_n = min(data_src.shape[0], round(end_n))
        else:
            _end_n = data_src.shape[0]

        start_n = min(_end_n, round(start_n))
        data_len = _end_n - start_n  # TODO: one-off to calculation below ?
        if data_len == 0:
            self._logger.warning("downsampling failed because of data_len = 0")
        iblock_len = min(self.max_elements, data_len)
        oblock_len = round(iblock_len / ds_factor)
        iterations = math.ceil(data_len / iblock_len)
        dest_len = math.floor(data_len / ds_factor)
        if data_dst is None:
            data_dst = np.empty((dest_len,))
        elif isinstance(data_dst, (h5py.Dataset, np.ndarray)):
            data_dst.resize((dest_len,))

        # 8th order butterworth filter for downsampling
        # note: cheby1 does not work well for static outputs
        # (2.8V can become 2.0V for constant buck-converters)
        filter_ = signal.iirfilter(
            N=8,
            Wn=1 / max(1.1, ds_factor),
            btype="lowpass",
            output="sos",
            ftype="butter",
        )
        # filter state - needed for sliced calculation
        f_state = np.zeros((filter_.shape[0], 2))

        slice_len = 0
        for _iter in trange(
            0,
            iterations,
            desc=f"downsampling {data_src.name}",
            leave=False,
            disable=iterations < 8,
        ):
            slice_ds = data_src[start_n + _iter * iblock_len : start_n + (_iter + 1) * iblock_len]
            if not is_time and ds_factor > 1:
                slice_ds, f_state = signal.sosfilt(filter_, slice_ds, zi=f_state)
            slice_ds = slice_ds[::ds_factor]
            slice_len = min(dest_len - _iter * oblock_len, oblock_len)
            data_dst[_iter * oblock_len : (_iter + 1) * oblock_len] = slice_ds[:slice_len]
        if isinstance(data_dst, np.ndarray):
            data_dst.resize((oblock_len * (iterations - 1) + slice_len,), refcheck=False)
        else:
            data_dst.resize((oblock_len * (iterations - 1) + slice_len,))
        return data_dst

    def resample(
        self,
        data_src: h5py.Dataset,
        data_dst: Union[None, h5py.Dataset, np.ndarray],
        start_n: int = 0,
        end_n: Optional[int] = None,
        samplerate_dst: float = 1000,
        *,
        is_time: bool = False,
    ) -> Union[h5py.Dataset, np.ndarray]:
        """:param data_src:
        :param data_dst:
        :param start_n:
        :param end_n:
        :param samplerate_dst:
        :param is_time:
        :return:
        """
        self._logger.error("Resampling is still under construction - do not use for now!")
        if self.get_datatype() == "ivcurve":
            self._logger.warning("Resampling-Function was not written for IVCurves")

        if isinstance(end_n, (int, float)):
            _end_n = min(data_src.shape[0], round(end_n))
        else:
            _end_n = data_src.shape[0]

        start_n = min(_end_n, round(start_n))
        data_len = _end_n - start_n
        if data_len == 0:
            self._logger.warning("resampling failed because of data_len = 0")
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
            """
            resampler = samplerate.Resampler(
                "sinc_medium",
                channels=1,
            )  # sinc_best, _medium, _fastest or linear
            for _iter in trange(
                0,
                iterations,
                desc=f"resampling {data_src.name}",
                leave=False,
                disable=iterations < 8,
            ):
                slice_inp_ds = data_src[slice_inp_now : slice_inp_now + slice_inp_len]
                slice_inp_now += slice_inp_len
                slice_out_ds = resampler.process(
                    slice_inp_ds, fs_ratio, _iter == iterations - 1, verbose=True
                )
                # slice_out_ds = resampy.resample(slice_inp_ds, self.samplerate_sps,
                #                                 samplerate_dst, filter="kaiser_fast")
                slice_out_nxt = slice_out_now + slice_out_ds.shape[0]
                # print(f"@{i}: got {slice_out_ds.shape[0]}")  # noqa: E800
                data_dst[slice_out_now:slice_out_nxt] = slice_out_ds
                slice_out_now = slice_out_nxt
            resampler.reset()
            """

        if isinstance(data_dst, np.ndarray):
            data_dst.resize((slice_out_now,), refcheck=False)
        else:
            data_dst.resize((slice_out_now,))

        return data_dst

    def generate_plot_data(
        self,
        start_s: Optional[float] = None,
        end_s: Optional[float] = None,
        *,
        relative_timestamp: bool = True,
    ) -> Dict:
        """Provides down-sampled iv-data that can be feed into plot_to_file()

        :param start_s: time in seconds, relative to start of recording
        :param end_s: time in seconds, relative to start of recording
        :param relative_timestamp: treat
        :return: down-sampled size of ~ self.max_elements
        """
        if self.get_datatype() == "ivcurve":
            self._logger.warning("Plot-Function was not written for IVCurves")
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
            "time": self._cal.time.raw_to_si(
                self.downsample(
                    self.ds_time,
                    None,
                    start_sample,
                    end_sample,
                    ds_factor,
                    is_time=True,
                )
            ).astype(float),
            "voltage": self._cal.voltage.raw_to_si(
                self.downsample(self.ds_voltage, None, start_sample, end_sample, ds_factor)
            ),
            "current": self._cal.current.raw_to_si(
                self.downsample(self.ds_current, None, start_sample, end_sample, ds_factor)
            ),
            "start_s": start_s,
            "end_s": end_s,
        }
        if relative_timestamp:
            data["time"] = data["time"] - self._cal.time.raw_to_si(self.ds_time[0])
        return data

    @staticmethod
    def assemble_plot(data: Union[dict, list], width: int = 20, height: int = 10) -> plt.Figure:
        """TODO: add power (if wanted)

        :param data: plottable / down-sampled iv-data with some meta-data
                -> created with generate_plot_data()
        :param width: plot-width
        :param height: plot-height
        :return:
        """
        if isinstance(data, dict):
            data = [data]
        fig, axes = plt.subplots(2, 1, sharex="all")
        fig.suptitle("Voltage and current")
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
        start_s: Optional[float] = None,
        end_s: Optional[float] = None,
        width: int = 20,
        height: int = 10,
    ) -> None:
        """Creates (down-sampled) IV-Plot
            -> omitting start- and end-time will use the whole duration

        :param start_s: time in seconds, relative to start of recording, optional
        :param end_s: time in seconds, relative to start of recording, optional
        :param width: plot-width
        :param height: plot-height
        """
        if not isinstance(self.file_path, Path):
            return

        data = [self.generate_plot_data(start_s, end_s)]

        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = self.file_path.resolve().with_suffix(f".plot_{start_str}_to_{end_str}.png")
        if plot_path.exists():
            self._logger.warning("Plot exists, will skip & not overwrite!")
            return
        self._logger.info("Plot generated, will be saved to '%s'", plot_path.name)
        fig = self.assemble_plot(data, width, height)
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()

    @staticmethod
    def multiplot_to_file(
        data: list, plot_path: Path, width: int = 20, height: int = 10
    ) -> Optional[Path]:
        """Creates (down-sampled) IV-Multi-Plot

        :param data: plottable / down-sampled iv-data with some meta-data
            -> created with generate_plot_data()
        :param plot_path: optional
        :param width: plot-width
        :param height: plot-height
        """
        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = (
            Path(plot_path).resolve().with_suffix(f".multiplot_{start_str}_to_{end_str}.png")
        )
        if plot_path.exists():
            logger.warning("Plot exists, will skip & not overwrite!")
            return None
        fig = Reader.assemble_plot(data, width, height)
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()
        return plot_path
