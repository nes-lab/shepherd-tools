"""
Reader-Baseclass
"""
import contextlib
import math
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import h5py
import numpy as np
import pandas as pd
import yaml
from matplotlib import pyplot as plt
from scipy import signal
from tqdm import trange

from shepherd_core import BaseReader
from shepherd_core import raw_to_si

# import samplerate  # TODO: just a test-fn for now


class Reader(BaseReader):
    """Sequentially Reads shepherd-data from HDF5 file.

    Args:
        file_path: Path of hdf5 file containing shepherd data with iv-samples, iv-curves or isc&voc
        verbose: more info during usage, 'None' skips the setter
    """

    def __init__(self, file_path: Optional[Path], verbose: Optional[bool] = True):
        super().__init__(file_path, verbose)

    def __repr__(self):
        return yaml.safe_dump(
            self.get_metadata(minimal=True), default_flow_style=False, sort_keys=False
        )

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
            round(float(j) * 1e-9 / self.samples_per_buffer, 6)
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
        return len(diffs) <= 1

    def get_metadata(
        self, node: Union[h5py.Dataset, h5py.Group, None] = None, minimal: bool = False
    ) -> Dict[str, dict]:
        """recursive FN to capture the structure of the file

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
                "dtype": str(node.dtype),
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
                # TODO: why not isinstance? can it be list[int] other complex type?
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
        if isinstance(self._file_path, Path):
            yml_path = Path(self._file_path).absolute().with_suffix(".yml")
            if yml_path.exists():
                self._logger.info("%s already exists, will skip", yml_path)
                return {}
            metadata = self.get_metadata(
                node
            )  # {"h5root": self.get_metadata(self.h5file)}
            with open(yml_path, "w", encoding="utf-8-sig") as yfd:
                yaml.safe_dump(metadata, yfd, default_flow_style=False, sort_keys=False)
        else:
            metadata = {}
        return metadata

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
            voltage_v = raw_to_si(
                self.ds_voltage[idx_start:idx_stop], self._cal["voltage"]
            )
            current_a = raw_to_si(
                self.ds_current[idx_start:idx_stop], self._cal["current"]
            )
            return (voltage_v[:] * current_a[:]).sum() * self.sample_interval_s

        energy_ws = [_calc_energy(i) for i in job_iter]
        return float(sum(energy_ws))

    def _dset_statistics(
        self, dset: h5py.Dataset, cal: Optional[dict] = None
    ) -> Dict[str, float]:
        """some basic stats for a provided dataset
        :param dset: dataset to evaluate
        :param cal: calibration (if wanted)
        :return: dict with entries for mean, min, max, std
        """
        if not isinstance(cal, dict):
            if "gain" in dset.attrs and "offset" in dset.attrs:
                cal = {
                    "gain": dset.attrs["gain"],
                    "offset": dset.attrs["offset"],
                    "si_converted": True,
                }
            else:
                cal = {"gain": 1, "offset": 0, "si_converted": False}
        else:
            cal["si_converted"] = True
        iterations = math.ceil(dset.shape[0] / self.max_elements)
        job_iter = trange(
            0,
            dset.shape[0],
            self.max_elements,
            desc=f"{dset.name}-stats",
            leave=False,
            disable=iterations < 8,
        )

        def _calc_statistics(data: np.ndarray) -> dict:
            return {
                "mean": np.mean(data),
                "min": np.min(data),
                "max": np.max(data),
                "std": np.std(data),
            }

        stats_list = [
            _calc_statistics(raw_to_si(dset[i : i + self.max_elements], cal))
            for i in job_iter
        ]
        if len(stats_list) < 1:
            return {}
        stats_df = pd.DataFrame(stats_list)
        stats: Dict[str, float] = {
            # TODO: wrong calculation for ndim-datasets with n>1
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
            self._logger.warning("%s is empty, no csv generated", h5_group.name)
            return 0
        if not isinstance(self._file_path, Path):
            return 0
        csv_path = self._file_path.with_suffix(f".{h5_group.name.strip('/')}.csv")
        if csv_path.exists():
            self._logger.warning("%s already exists, will skip", csv_path)
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
        with open(csv_path, "w", encoding="utf-8-sig") as csv_file:
            self._logger.info(
                "CSV-Generator will save '%s' to '%s'", h5_group.name, csv_path.name
            )
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
            self._logger.warning("%s is empty, no log generated", h5_group.name)
            return 0
        if not isinstance(self._file_path, Path):
            return 0
        log_path = self._file_path.with_suffix(f".{h5_group.name.strip('/')}.log")
        if log_path.exists():
            self._logger.warning("%s already exists, will skip", log_path)
            return 0
        datasets = [
            key if isinstance(h5_group[key], h5py.Dataset) else []
            for key in h5_group.keys()
        ]
        datasets.remove("time")
        with open(log_path, "w", encoding="utf-8-sig") as log_file:
            self._logger.info(
                "Log-Generator will save '%s' to '%s'", h5_group.name, log_path.name
            )
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
        end_n: Optional[int] = None,
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
            slice_ds = data_src[
                start_n + _iter * iblock_len : start_n + (_iter + 1) * iblock_len
            ]
            if not is_time and ds_factor > 1:
                slice_ds, f_state = signal.sosfilt(filter_, slice_ds, zi=f_state)
            slice_ds = slice_ds[::ds_factor]
            slice_len = min(dest_len - _iter * oblock_len, oblock_len)
            data_dst[_iter * oblock_len : (_iter + 1) * oblock_len] = slice_ds[
                :slice_len
            ]
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
        end_n: Optional[int] = None,
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
        self._logger.error(
            "Resampling is still under construction - do not use for now!"
        )
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
            pass

        if isinstance(data_dst, np.ndarray):
            data_dst.resize((slice_out_now,), refcheck=False)
        else:
            data_dst.resize((slice_out_now,))

        return data_dst

    def generate_plot_data(
        self,
        start_s: Optional[float] = None,
        end_s: Optional[float] = None,
        relative_ts: bool = True,
    ) -> Dict:
        """provides down-sampled iv-data that can be feed into plot_to_file()

        :param start_s: time in seconds, relative to start of recording
        :param end_s: time in seconds, relative to start of recording
        :param relative_ts: treat
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
            "time": self.downsample(
                self.ds_time, None, start_sample, end_sample, ds_factor, is_time=True
            ).astype(float)
            * 1e-9,
            "voltage": raw_to_si(
                self.downsample(
                    self.ds_voltage, None, start_sample, end_sample, ds_factor
                ),
                self._cal["voltage"],
            ),
            "current": raw_to_si(
                self.downsample(
                    self.ds_current, None, start_sample, end_sample, ds_factor
                ),
                self._cal["current"],
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
        """creates (down-sampled) IV-Plot
            -> omitting start- and end-time will use the whole duration

        :param start_s: time in seconds, relative to start of recording, optional
        :param end_s: time in seconds, relative to start of recording, optional
        :param width: plot-width
        :param height: plot-height
        """
        if not isinstance(self._file_path, Path):
            return

        data = [self.generate_plot_data(start_s, end_s)]

        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = self._file_path.absolute().with_suffix(
            f".plot_{start_str}_to_{end_str}.png"
        )
        if plot_path.exists():
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
        """creates (down-sampled) IV-Multi-Plot

        :param data: plottable / down-sampled iv-data with some meta-data
            -> created with generate_plot_data()
        :param plot_path: optional
        :param width: plot-width
        :param height: plot-height
        """
        start_str = f"{data[0]['start_s']:.3f}".replace(".", "s")
        end_str = f"{data[0]['end_s']:.3f}".replace(".", "s")
        plot_path = (
            Path(plot_path)
            .absolute()
            .with_suffix(f".multiplot_{start_str}_to_{end_str}.png")
        )
        if plot_path.exists():
            return None
        fig = Reader.assemble_plot(data, width, height)
        plt.savefig(plot_path)
        plt.close(fig)
        plt.clf()
        return plot_path
